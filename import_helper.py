import pandas as pd
import os
import re

def parse_csv_data(csv_path):
    """
    Parses the new flat CSV layout (Database export).
    """
    
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return []

    # Read with header on row 2 (index 1)
    try:
        df = pd.read_csv(csv_path, header=1)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return []

    records = []
    id_counter = 1
    
    for _, row in df.iterrows():
        # Check mandatory fields
        shipper = str(row.get('SHIPPER', '')).strip()
        if not shipper or shipper.lower() == 'nan':
            continue
            
        area = str(row.get('Area', '')).strip()
        jenis = str(row.get('Jenis Perjanjian', '')).strip()
        no_perjanjian = str(row.get('NO. PERJANJIAN (TRANSPORTER)', '')).strip()
        tgl_perjanjian = str(row.get('TGL PERJANJIAN', '')).strip()
        start_date = str(row.get('Start', '')).strip()
        end_date = str(row.get('End', '')).strip()
        raw_status = str(row.get('Status', '')).strip()
        
        # Status Mapping
        status_override = 'safe'
        s_lower = raw_status.lower()
        if 'need follow up' in s_lower:
            status_override = 'urgent'
        elif 'need action' in s_lower:
             status_override = 'pending'
        elif 'done' in s_lower:
            status_override = 'done'
        elif 'terminate' in s_lower or 'expired' in s_lower:
            status_override = 'expired'
        elif 'existing' in s_lower:
             status_override = 'safe'
        
        # Clean dates (Pandas might have parsed them or they are strings)
        # If they are strings like '12/23/2025', we keep them as strings for now, 
        # but app.py expects ISO or datetime objects to convert.
        # Let's try to convert to YYYY-MM-DD for consistency
        try:
             if start_date and start_date.lower() != 'nan':
                 start_date = pd.to_datetime(start_date).strftime('%Y-%m-%d')
             else:
                 start_date = '-'
                 
             if end_date and end_date.lower() != 'nan':
                 end_date = pd.to_datetime(end_date).strftime('%Y-%m-%d')
             else:
                 end_date = '-'

             if tgl_perjanjian and tgl_perjanjian.lower() != 'nan':
                 tgl_perjanjian = pd.to_datetime(tgl_perjanjian).strftime('%Y-%m-%d')
             else:
                 tgl_perjanjian = '-'
        except:
             pass # Keep as original string if parse fails

        record = {
            "ID": f"CUST-{id_counter:03d}",
            "Nama Perusahaan": shipper,
            "Region": area,
            "Jenis Perjanjian": jenis,
            "No Perjanjian": no_perjanjian,
            "Status Asli": raw_status,
            "Tanggal Perjanjian": tgl_perjanjian,
            "Tanggal Mulai": start_date,
            "Tanggal Berakhir": end_date,
            "Status Override": status_override,
            "Notes": f"Imported from Database CSV."
        }
        records.append(record)
        id_counter += 1
            
    return records

if __name__ == "__main__":
    # Test run
    target_csv = "Copy of MONITORING PERJANJIAN KOMERSIAL FUNGSI COMMERCIAL CAPACITY - Database.csv"
    path = os.path.join(os.path.dirname(__file__), "..", target_csv)
    
    print(f"Testing import from {path}")
    data = parse_csv_data(path)
    print(f"Parsed {len(data)} records.")
    if len(data) > 0:
        print("Sample:", data[0])
