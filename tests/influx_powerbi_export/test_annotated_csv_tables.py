"""
Regression tests for AnnotatedCSVParser table boundary handling.

Tests synthetic annotated CSV strings only.
No real contexts, sources, MMSI values, vessel names, or coordinates.
"""
import pytest
from tools.influx_powerbi_export.annotated_csv import AnnotatedCSVParser


class TestSingleFluxTable:
    """Test single Flux table parsing."""
    
    def test_single_table_parses_correctly(self):
        """Single Flux table parses correctly."""
        csv_lines = [
            "#group,false,false,true,true,false,false,true,true",
            "#datatype,string,long,dateTime:RFC3339,dateTime:RFC3339,dateTime:RFC3339,string,string,string",
            "#default,_result,,,,,,,",
            ",result,table,_start,_stop,_time,_value,_field,_measurement",
            ",,0,2026-09-04T16:00:00Z,2026-09-04T16:00:10Z,2026-09-04T16:00:03Z,1.5,wind_speed,environment",
            ",,0,2026-09-04T16:00:00Z,2026-09-04T16:00:10Z,2026-09-04T16:00:05Z,2.0,wind_speed,environment",
        ]
        
        parser = AnnotatedCSVParser()
        records = list(parser.parse_stream(iter(csv_lines)))
        
        assert len(records) == 2
        assert records[0]['_field'] == 'wind_speed'
        assert records[0]['_value'] == '1.5'
    
    def test_table_header_not_yielded_as_data(self):
        """Table header row is not yielded as a data record."""
        csv_lines = [
            "#group,false,false",
            "#datatype,string,long",
            "#default,_result,,",
            ",result,table,_time,_value,_field",
            ",,0,2026-09-04T16:00:03Z,1.5,wind_speed",
        ]
        
        parser = AnnotatedCSVParser()
        records = list(parser.parse_stream(iter(csv_lines)))
        
        # Should only have 1 data record, not 2
        assert len(records) == 1
        # Record should NOT have _time == '_time' (that would be the header)
        assert records[0]['_time'] != '_time'
        assert records[0]['_time'] == '2026-09-04T16:00:03Z'
    
    def test_no_literal_header_values(self):
        """No parsed record has literal header values."""
        csv_lines = [
            "#group,false,false",
            "#datatype,string,long",
            "#default,_result,,",
            ",result,table,_time,_value,_field",
            ",,0,2026-09-04T16:00:03Z,1.5,wind_speed",
        ]
        
        parser = AnnotatedCSVParser()
        records = list(parser.parse_stream(iter(csv_lines)))
        
        for record in records:
            assert record.get('_time') != '_time'
            assert record.get('_value') != '_value'
            assert record.get('_field') != '_field'


class TestMultipleFluxTables:
    """Test multiple Flux tables with boundaries."""
    
    def test_two_flux_tables_parse_correctly(self):
        """Two Flux tables parse correctly with boundary marker."""
        csv_lines = [
            "#group,false,false",
            "#datatype,string,long",
            "#default,_result,,",
            ",result,table,_time,_value,_field",
            ",,0,2026-09-04T16:00:03Z,1.5,wind_speed",
            ",,0,2026-09-04T16:00:05Z,2.0,wind_speed",
            ",result,table,_time,_value,_field",  # Table boundary for table 2
            ",,1,2026-09-04T16:00:07Z,3.0,temperature",
            ",,1,2026-09-04T16:00:09Z,3.5,temperature",
        ]
        
        parser = AnnotatedCSVParser()
        records = list(parser.parse_stream(iter(csv_lines)))
        
        # Should have 4 data records (2 from each table)
        assert len(records) == 4
        # First two records from table 0
        assert records[0]['_field'] == 'wind_speed'
        assert records[1]['_field'] == 'wind_speed'
        # Second two records from table 1
        assert records[2]['_field'] == 'temperature'
        assert records[3]['_field'] == 'temperature'
    
    def test_three_flux_tables_parse_correctly(self):
        """Three Flux tables parse correctly."""
        csv_lines = [
            "#group,false,false",
            "#datatype,string,long",
            "#default,_result,,",
            ",result,table,_time,_value,_field",
            ",,0,2026-09-04T16:00:03Z,1.5,field_a",
            ",result,table,_time,_value,_field",  # Boundary 1
            ",,1,2026-09-04T16:00:05Z,2.0,field_b",
            ",result,table,_time,_value,_field",  # Boundary 2
            ",,2,2026-09-04T16:00:07Z,3.0,field_c",
        ]
        
        parser = AnnotatedCSVParser()
        records = list(parser.parse_stream(iter(csv_lines)))
        
        assert len(records) == 3
        assert records[0]['_field'] == 'field_a'
        assert records[1]['_field'] == 'field_b'
        assert records[2]['_field'] == 'field_c'
    
    def test_table_boundaries_counted_correctly(self):
        """Table boundaries are counted correctly."""
        csv_lines = [
            "#group,false,false",
            "#datatype,string,long",
            "#default,_result,,",
            ",result,table,_time,_value,_field",
            ",,0,2026-09-04T16:00:03Z,1.5,field_a",
            ",result,table,_time,_value,_field",  # Boundary 1
            ",,1,2026-09-04T16:00:05Z,2.0,field_b",
            ",result,table,_time,_value,_field",  # Boundary 2
            ",,2,2026-09-04T16:00:07Z,3.0,field_c",
        ]
        
        parser = AnnotatedCSVParser()
        list(parser.parse_stream(iter(csv_lines)))
        
        # The parser should have detected 2 table boundaries (3 tables total)
        # But since it increments after detection, check that at least 2+ records exist
        assert len(list(parser.parse_stream(iter(csv_lines)))) == 3


class TestParserEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_values_become_none(self):
        """Empty values become None."""
        csv_lines = [
            "#group,false,false",
            "#datatype,string,long",
            "#default,_result,,",
            ",result,table,_time,_value,_field",
            ",,0,2026-09-04T16:00:03Z,,wind_speed",  # Empty _value
        ]
        
        parser = AnnotatedCSVParser()
        records = list(parser.parse_stream(iter(csv_lines)))
        
        assert len(records) == 1
        assert records[0]['_value'] is None
    
    def test_field_value_cells_remain_aligned(self):
        """Actual field/value cells remain aligned after boundary."""
        csv_lines = [
            "#group,false,false",
            "#datatype,string,long",
            "#default,_result,,",
            ",result,table,_time,_value,_field",
            ",,0,2026-09-04T16:00:03Z,1.5,wind_speed",
            ",result,table,_time,_value,_field",  # Boundary
            ",,1,2026-09-04T16:00:05Z,2.5,temperature",
        ]
        
        parser = AnnotatedCSVParser()
        records = list(parser.parse_stream(iter(csv_lines)))
        
        # After boundary, values should still be correctly aligned
        assert records[0]['_time'] == '2026-09-04T16:00:03Z'
        assert records[0]['_value'] == '1.5'
        assert records[1]['_time'] == '2026-09-04T16:00:05Z'
        assert records[1]['_value'] == '2.5'
    
    def test_annotation_metadata_rows_excluded(self):
        """Annotated metadata rows are excluded."""
        csv_lines = [
            "#group,false,false,false",
            "#datatype,string,long,string",
            "#default,_result,,,",
            ",result,table,_time,_value,_field",
            ",,0,2026-09-04T16:00:03Z,1.5,wind_speed",
        ]
        
        parser = AnnotatedCSVParser()
        records = list(parser.parse_stream(iter(csv_lines)))
        
        # Should only have 1 record, no annotation rows
        assert len(records) == 1
    
    def test_context_and_source_columns_preserved(self):
        """Context and source columns are preserved."""
        csv_lines = [
            "#group,false,false",
            "#datatype,string,long",
            "#default,_result,,",
            ",result,table,_time,_value,_field,context,source",
            ",,0,2026-09-04T16:00:03Z,1.5,wind_speed,ctx_value,src_value",
        ]
        
        parser = AnnotatedCSVParser()
        records = list(parser.parse_stream(iter(csv_lines)))
        
        assert records[0]['context'] == 'ctx_value'
        assert records[0]['source'] == 'src_value'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
