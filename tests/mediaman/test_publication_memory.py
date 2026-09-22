"""Publication memory: persistence across runs and mode-aware identity.

A publication state store named "memory" must remember publications
between executions, not only within one. And a rehearsal must never
consume the slot of a real publication: the mode belongs to the identity.

No network access, no credentials, no Telegram. Offline only.
"""
import hashlib
import os
import stat

import pytest

from mediaman.historical_entrypoint import (
    CHEMIN_ETAT_DEFAUT,
    MODES_PUBLICATION,
    SENTINELLE_ETAT_EPHEMERE,
    derive_publication_id,
    open_publication_store,
    resolve_state_db_path,
)
from mediaman.publication_state import (
    PublicationState,
    PublicationStateRecord,
    PublicationStateStore,
)


def _record(pub_id, race_id="race-1"):
    return PublicationStateRecord(
        publication_id=pub_id,
        race_id=race_id,
        cycle_id="historical-2026-09-07T14:36:24Z",
        state=PublicationState.READY,
        created_at="2026-09-22T00:00:00Z",
        updated_at="2026-09-22T00:00:00Z",
    )


class TestResolveStateDbPath:
    def test_default_is_under_home_and_named_publications(self):
        chemin = resolve_state_db_path(environ={})
        assert chemin == os.path.expanduser(CHEMIN_ETAT_DEFAUT)
        assert chemin.startswith(os.path.expanduser("~"))
        assert chemin.endswith("publications.db")

    def test_default_is_outside_the_repository(self):
        racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        chemin = resolve_state_db_path(environ={}, repo_root=racine)
        assert not chemin.startswith(racine + os.sep)

    def test_empty_value_falls_back_to_default(self):
        assert resolve_state_db_path(environ={"MEDIAMAN_STATE_DB": "   "}) == \
            os.path.expanduser(CHEMIN_ETAT_DEFAUT)

    def test_sentinel_keeps_the_ephemeral_behaviour(self):
        assert resolve_state_db_path(
            environ={"MEDIAMAN_STATE_DB": SENTINELLE_ETAT_EPHEMERE}
        ) == SENTINELLE_ETAT_EPHEMERE

    def test_explicit_path_is_honoured_and_absolute(self, tmp_path):
        cible = tmp_path / "ailleurs" / "p.db"
        assert resolve_state_db_path(environ={"MEDIAMAN_STATE_DB": str(cible)}) == str(cible)

    def test_path_inside_the_repository_is_refused(self, tmp_path):
        racine = str(tmp_path / "depot")
        os.makedirs(racine)
        with pytest.raises(ValueError, match="depot"):
            resolve_state_db_path(
                environ={"MEDIAMAN_STATE_DB": os.path.join(racine, "logs", "p.db")},
                repo_root=racine,
            )

    def test_existing_directory_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="repertoire"):
            resolve_state_db_path(environ={"MEDIAMAN_STATE_DB": str(tmp_path)})


class TestDerivePublicationId:
    CANON = dict(race_id="race-1", as_of_utc="2026-09-07T14:36:24Z",
                 window_seconds=300, content="bulletin")

    def test_is_sha256_hexadecimal(self):
        pid = derive_publication_id(mode="dry-run", **self.CANON)
        assert len(pid) == 64 and all(c in "0123456789abcdef" for c in pid)

    def test_is_deterministic(self):
        assert derive_publication_id(mode="dry-run", **self.CANON) == \
            derive_publication_id(mode="dry-run", **self.CANON)

    def test_a_rehearsal_and_a_real_publication_are_two_identities(self):
        """Le coeur du chantier : un tir a blanc ne doit pas consommer
        le creneau d une vraie publication."""
        assert derive_publication_id(mode="dry-run", **self.CANON) != \
            derive_publication_id(mode="live", **self.CANON)

    def test_unknown_mode_is_refused(self):
        with pytest.raises(ValueError, match="mode"):
            derive_publication_id(mode="blanc", **self.CANON)

    def test_every_declared_mode_is_accepted(self):
        for mode in MODES_PUBLICATION:
            assert len(derive_publication_id(mode=mode, **self.CANON)) == 64

    def test_content_change_changes_the_identity(self):
        autre = dict(self.CANON, content="bulletin different")
        assert derive_publication_id(mode="dry-run", **self.CANON) != \
            derive_publication_id(mode="dry-run", **autre)

    def test_window_change_changes_the_identity(self):
        autre = dict(self.CANON, window_seconds=600)
        assert derive_publication_id(mode="dry-run", **self.CANON) != \
            derive_publication_id(mode="dry-run", **autre)

    def test_mode_is_the_first_field_of_the_canonical_string(self):
        attendu = hashlib.sha256(
            "dry-run:race-1:2026-09-07T14:36:24Z:300:bulletin".encode("utf-8")
        ).hexdigest()
        assert derive_publication_id(mode="dry-run", **self.CANON) == attendu


class TestOpenPublicationStore:
    def test_ephemeral_store_leaves_nothing_behind(self):
        with open_publication_store(SENTINELLE_ETAT_EPHEMERE) as (store, nature):
            assert nature == "ephemere"
            chemin = store.db_path
            assert os.path.exists(chemin)
        assert not os.path.exists(chemin)

    def test_persistent_store_survives_the_context(self, tmp_path):
        chemin = str(tmp_path / "etat" / "publications.db")
        with open_publication_store(chemin) as (store, nature):
            assert nature == "persistant"
        assert os.path.exists(chemin)

    def test_parent_directory_is_created_private(self, tmp_path):
        chemin = str(tmp_path / "prive" / "publications.db")
        with open_publication_store(chemin):
            pass
        mode = stat.S_IMODE(os.stat(os.path.dirname(chemin)).st_mode)
        assert mode == 0o700, oct(mode)

    def test_a_publication_is_remembered_between_two_runs(self, tmp_path):
        """Le coeur du chantier : deux executions, une seule publication."""
        chemin = str(tmp_path / "publications.db")
        pid = derive_publication_id(mode="dry-run", race_id="race-1",
                                    as_of_utc="2026-09-07T14:36:24Z",
                                    window_seconds=300, content="bulletin")
        with open_publication_store(chemin) as (store, _):
            assert store.create(_record(pid)) is True
        with open_publication_store(chemin) as (store, _):
            assert store.get(pid) is not None
            assert store.create(_record(pid)) is False

    def test_the_ephemeral_store_forgets_between_two_runs(self):
        """Contre-preuve : l ancien comportement ne memorisait rien."""
        pid = "b" * 64
        with open_publication_store(SENTINELLE_ETAT_EPHEMERE) as (store, _):
            assert store.create(_record(pid)) is True
        with open_publication_store(SENTINELLE_ETAT_EPHEMERE) as (store, _):
            assert store.get(pid) is None

    def test_rehearsal_and_real_publication_coexist(self, tmp_path):
        chemin = str(tmp_path / "publications.db")
        canon = dict(race_id="race-1", as_of_utc="2026-09-07T14:36:24Z",
                     window_seconds=300, content="bulletin")
        blanc = derive_publication_id(mode="dry-run", **canon)
        reel = derive_publication_id(mode="live", **canon)
        with open_publication_store(chemin) as (store, _):
            assert store.create(_record(blanc)) is True
            assert store.create(_record(reel)) is True
            assert store.get(reel) is not None


class TestSuiteIsolation:
    """La suite de tests ne doit jamais ecrire dans la memoire de l operateur."""

    def _fichiers_de_test(self):
        base = os.path.dirname(os.path.abspath(__file__))
        return [os.path.join(base, f) for f in sorted(os.listdir(base))
                if f.startswith("test_") and f.endswith(".py")]

    def test_no_historical_chain_test_runs_without_isolating_the_memory(self):
        """Mesure : un fichier qui importe la chaine historique ET regle
        DRY_RUN doit aussi regler MEDIAMAN_STATE_DB. Regler DRY_RUN sans
        toucher a cette chaine ne concerne pas la memoire des publications."""
        fautifs = []
        for chemin in self._fichiers_de_test():
            src = open(chemin, encoding="utf-8").read()
            touche_chaine = "historical_entrypoint" in src
            regle_dry_run = "'DRY_RUN': 'true'" in src or '"DRY_RUN": "true"' in src
            if touche_chaine and regle_dry_run and "MEDIAMAN_STATE_DB" not in src:
                fautifs.append(os.path.basename(chemin))
        assert fautifs == [], f"tests sans memoire isolee : {fautifs}"

    def test_a_chain_run_does_not_create_the_default_memory(self, tmp_path):
        """Mesure a l execution : la chaine lancee avec la sentinelle ne
        cree pas ~/.mediaman/publications.db."""
        from unittest.mock import Mock, patch

        from mediaman.historical_entrypoint import main
        from mediaman.mcp_collector import (
            CollectionResult,
            CollectionStatus,
            NavigationFact,
            Provenance,
        )

        defaut = os.path.expanduser(CHEMIN_ETAT_DEFAUT)
        if os.path.exists(defaut):
            pytest.skip("une memoire par defaut existe deja sur cette machine")

        prov = Provenance(tool_public_id="racing.get_historical_snapshot",
                          server_name="racing",
                          wire_tool_name="get_historical_snapshot",
                          source_id="mcp:racing:historical")
        faits = [NavigationFact(field_name=n, value=v, unit=u, provenance=prov)
                 for n, v, u in (("latitude", 41.2619, "decimal_degrees"),
                                 ("longitude", -73.1337, "decimal_degrees"),
                                 ("speed_over_ground", 5.5, "m/s"),
                                 ("course_over_ground", 180.0, "degrees_true"))]
        collecte = Mock()
        collecte.collect_historical = Mock(return_value=CollectionResult(
            status=CollectionStatus.COMPLETE, race_id="memoire-test", facts=faits,
            collection_start_at="2026-09-01T12:00:00Z",
            collection_end_at="2026-09-01T12:00:01Z"))
        serveur = tmp_path / "racing.js"
        serveur.write_text("// faux serveur MCP\n")
        serveur.chmod(0o755)

        env = {"MEDIAMAN_CONTENT_PROVIDER": "historical_mcp",
               "MEDIAMAN_RACE_ID": "memoire-test",
               "MEDIAMAN_HISTORICAL_AS_OF": "2026-09-01T12:00:00Z",
               "MEDIAMAN_HISTORICAL_WINDOW_SECONDS": "60",
               "MEDIAMAN_MCP_SERVER_PATH": str(serveur),
               "DRY_RUN": "true",
               "MEDIAMAN_STATE_DB": SENTINELLE_ETAT_EPHEMERE}
        with patch.dict(os.environ, env, clear=True), \
                patch("mediaman.historical_entrypoint.setup_service_logger", return_value=Mock()), \
                patch("mediaman.historical_entrypoint.MCPClient", return_value=Mock()), \
                patch("mediaman.historical_entrypoint.MCPCollector", return_value=collecte):
            code = main()
        assert code == 0
        assert not os.path.exists(defaut), "la chaine a cree la memoire par defaut"


class TestTwoIdenticalRuns:
    """Deux executions identiques : une seule publication, et un journal
    qui dit la verite sur la seconde."""

    def _lancer(self, memoire, envois, journal, memoire_env=None):
        from unittest.mock import Mock, patch

        import mediaman.historical_entrypoint as HE
        from mediaman.mcp_collector import (
            CollectionResult,
            CollectionStatus,
            NavigationFact,
            Provenance,
        )

        prov = Provenance(tool_public_id="racing.get_historical_snapshot",
                          server_name="racing",
                          wire_tool_name="get_historical_snapshot",
                          source_id="mcp:racing:historical")
        faits = [NavigationFact(field_name=n, value=v, unit=u, provenance=prov)
                 for n, v, u in (("latitude", 41.2619, "decimal_degrees"),
                                 ("longitude", -73.1337, "decimal_degrees"),
                                 ("speed_over_ground", 5.5, "m/s"),
                                 ("course_over_ground", 180.0, "degrees_true"))]
        col = Mock()
        col.collect_historical = Mock(return_value=CollectionResult(
            status=CollectionStatus.COMPLETE, race_id="deux-fois", facts=faits,
            collection_start_at="2026-09-01T12:00:00Z",
            collection_end_at="2026-09-01T12:00:01Z"))

        serveur = os.path.join(os.path.dirname(memoire), "racing.js")
        os.makedirs(os.path.dirname(serveur), exist_ok=True)
        open(serveur, "w").write("// faux serveur MCP\n")
        os.chmod(serveur, 0o755)

        class Journal:
            def __getattr__(self, niveau):
                return lambda msg, *a, **k: journal.append(f"{niveau.upper()} {msg}")

        vrai = HE.DryRunSender.send

        def compte(zelf, message, race_id=None, as_of_utc=None, window_seconds=None):
            envois.append(as_of_utc)
            return vrai(zelf, message, race_id=race_id, as_of_utc=as_of_utc,
                        window_seconds=window_seconds)

        env = {"MEDIAMAN_CONTENT_PROVIDER": "historical_mcp",
               "MEDIAMAN_RACE_ID": "deux-fois",
               "MEDIAMAN_HISTORICAL_AS_OF": "2026-09-01T12:00:00Z",
               "MEDIAMAN_HISTORICAL_WINDOW_SECONDS": "60",
               "MEDIAMAN_MCP_SERVER_PATH": serveur,
               "DRY_RUN": "true",
               "MEDIAMAN_STATE_DB": memoire_env or memoire}
        with patch.dict(os.environ, env, clear=True), \
                patch.object(HE.DryRunSender, "send", compte), \
                patch("mediaman.historical_entrypoint.setup_service_logger", return_value=Journal()), \
                patch("mediaman.historical_entrypoint.MCPClient", return_value=Mock()), \
                patch("mediaman.historical_entrypoint.MCPCollector", return_value=col):
            return HE.main()

    def _lancer_avec_sentinelle(self, ancre, envois, journal):
        """Meme lancement, mais la memoire est la sentinelle ephemere."""
        return self._lancer(ancre, envois, journal, memoire_env=SENTINELLE_ETAT_EPHEMERE)

    def test_two_identical_runs_send_exactly_once(self, tmp_path):
        memoire = str(tmp_path / "m" / "publications.db")
        envois, j1, j2 = [], [], []
        assert self._lancer(memoire, envois, j1) == 0
        assert len(envois) == 1
        assert self._lancer(memoire, envois, j2) == 0
        assert len(envois) == 1, "la seconde execution a renvoye"

    def test_the_second_run_says_that_nothing_was_sent(self, tmp_path):
        memoire = str(tmp_path / "m" / "publications.db")
        envois, j1, j2 = [], [], []
        self._lancer(memoire, envois, j1)
        self._lancer(memoire, envois, j2)
        assert any("publication published" in l for l in j1)
        assert not any("publication published" in l for l in j2), \
            "le journal annonce une publication qui n a pas eu lieu"
        assert any("nothing sent" in l for l in j2)
        assert any("already in memory" in l for l in j2)

    def test_an_ephemeral_memory_sends_twice(self, tmp_path):
        """Contre-preuve : l ancien comportement publiait deux fois."""
        envois, j1, j2 = [], [], []
        os.makedirs(tmp_path / "srv", exist_ok=True)
        (tmp_path / "srv" / "ancre").write_text("")
        for _ in range(2):
            self._lancer_avec_sentinelle(str(tmp_path / "srv" / "x"), envois, j1)
        assert len(envois) == 2, "la memoire ephemere aurait du oublier"


class TestSystemdConvention:
    """Meme convention que la chaine evenements : STATE_DIRECTORY d abord."""

    def test_systemd_state_directory_is_preferred_over_home(self, tmp_path):
        chemin = resolve_state_db_path(environ={"STATE_DIRECTORY": str(tmp_path)})
        assert chemin == str(tmp_path / "publications.db")

    def test_explicit_variable_wins_over_systemd(self, tmp_path):
        cible = tmp_path / "choisi.db"
        chemin = resolve_state_db_path(environ={
            "STATE_DIRECTORY": str(tmp_path / "systemd"),
            "MEDIAMAN_STATE_DB": str(cible)})
        assert chemin == str(cible)

    def test_only_the_first_systemd_directory_is_used(self, tmp_path):
        deux = f"{tmp_path}:{tmp_path}/autre"
        assert resolve_state_db_path(environ={"STATE_DIRECTORY": deux}) == \
            str(tmp_path / "publications.db")
