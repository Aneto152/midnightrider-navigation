"""
Data normalization: aggregation, circular means, window bucketing.
"""
import math
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

class Normalizer:
    """Normalize and aggregate InfluxDB data into 10-second windows."""
    
    CIRCULAR_FIELDS = {
        "cog_deg", "true_heading_deg", "awa_deg", "twa_deg", "tide_set_deg"
    }
    
    def __init__(self):
        self.windows = defaultdict(lambda: defaultdict(list))
    
    def add_point(self, timestamp_utc: str, field_name: str, value: Optional[float]):
        """Add a data point to its 10-second window."""
        if value is None or timestamp_utc is None:
            return
        
        try:
            # Convert ISO timestamp to seconds, then bucket to 10-second window
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp_utc.replace('Z', '+00:00'))
            seconds = dt.timestamp()
            window_start = int(seconds / 10) * 10
            window_key = (window_start, window_start + 10)
            
            self.windows[window_key][field_name].append(value)
        except:
            pass
    
    def aggregate_windows(self) -> List[Dict]:
        """Aggregate all windows, return normalized rows."""
        results = []
        
        for (window_start, window_end), fields in sorted(self.windows.items()):
            row = {
                "window_start_utc": self._epoch_to_iso(window_start),
                "window_end_utc": self._epoch_to_iso(window_end),
                "timestamp_utc": self._epoch_to_iso((window_start + window_end) / 2),
                "sample_count": sum(len(v) for v in fields.values()),
            }
            
            for field_name, values in fields.items():
                if not values:
                    row[field_name] = None
                elif field_name in self.CIRCULAR_FIELDS:
                    row[field_name] = self.circular_mean(values)
                else:
                    row[field_name] = sum(values) / len(values)
            
            row["completeness_ratio"] = row["sample_count"] / (len(fields) * 10) if fields else 0
            row["quality_flag"] = self._quality_flag(row["completeness_ratio"])
            
            results.append(row)
        
        return results
    
    def circular_mean(self, angles: List[float]) -> Optional[float]:
        """Compute circular mean of angles (degrees, 0-360)."""
        if not angles:
            return None
        
        # Convert to radians, compute mean direction
        radians = [math.radians(a % 360) for a in angles]
        sin_sum = sum(math.sin(r) for r in radians)
        cos_sum = sum(math.cos(r) for r in radians)
        
        mean_rad = math.atan2(sin_sum / len(radians), cos_sum / len(radians))
        mean_deg = math.degrees(mean_rad)
        
        # Convert back to 0-360 range
        return mean_deg if mean_deg >= 0 else mean_deg + 360
    
    def _quality_flag(self, completeness: float) -> str:
        """Generate quality flag based on completeness."""
        if completeness >= 0.75:
            return "GOOD"
        elif completeness >= 0.50:
            return "POOR"
        else:
            return "MISSING"
    
    def _epoch_to_iso(self, seconds: float) -> str:
        """Convert Unix timestamp to ISO8601."""
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
        return dt.isoformat().replace('+00:00', 'Z')
