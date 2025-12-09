"""
Attorney Database Models
========================
SQLite database schema for attorney recruiting data.
"""

import sqlite3
import os
from datetime import datetime

DATABASE_FILE = "attorneys.db"


def get_connection(db_path=DATABASE_FILE):
    """Get database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_database(db_path=DATABASE_FILE):
    """Initialize the database with all tables."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Attorneys table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attorneys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bar_number TEXT,
            state TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            full_name TEXT NOT NULL,
            status TEXT,
            admission_date TEXT,
            firm_name TEXT,
            city TEXT,
            county TEXT,
            address TEXT,
            email TEXT,
            phone TEXT,
            website TEXT,
            law_school TEXT,
            graduation_year TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(bar_number, state)
        )
    """)
    
    # Practice areas table (many-to-many)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS practice_areas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attorney_id INTEGER NOT NULL,
            practice_area TEXT NOT NULL,
            is_primary BOOLEAN DEFAULT 0,
            FOREIGN KEY (attorney_id) REFERENCES attorneys(id),
            UNIQUE(attorney_id, practice_area)
        )
    """)
    
    # Firms table (for deduplication and enrichment)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS firms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            website TEXT,
            city TEXT,
            state TEXT,
            address TEXT,
            phone TEXT,
            size_estimate TEXT,
            attorney_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, city, state)
        )
    """)
    
    # Scrape logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scrape_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state TEXT NOT NULL,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            attorneys_found INTEGER DEFAULT 0,
            attorneys_added INTEGER DEFAULT 0,
            attorneys_updated INTEGER DEFAULT 0,
            errors INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running',
            notes TEXT
        )
    """)
    
    # Create indexes for common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_attorneys_state ON attorneys(state)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_attorneys_status ON attorneys(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_attorneys_firm ON attorneys(firm_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_attorneys_city ON attorneys(city)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_practice_areas_area ON practice_areas(practice_area)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_attorneys_name ON attorneys(last_name, first_name)")
    
    conn.commit()
    conn.close()
    
    print(f"✅ Database initialized: {db_path}")


def insert_attorney(conn, attorney_data):
    """Insert or update an attorney record."""
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO attorneys (
                bar_number, state, first_name, last_name, full_name,
                status, admission_date, firm_name, city, county,
                address, email, phone, website, law_school, graduation_year
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(bar_number, state) DO UPDATE SET
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                full_name = excluded.full_name,
                status = excluded.status,
                firm_name = excluded.firm_name,
                city = excluded.city,
                county = excluded.county,
                address = excluded.address,
                email = excluded.email,
                phone = excluded.phone,
                website = excluded.website,
                updated_at = CURRENT_TIMESTAMP
        """, (
            attorney_data.get('bar_number'),
            attorney_data.get('state'),
            attorney_data.get('first_name'),
            attorney_data.get('last_name'),
            attorney_data.get('full_name'),
            attorney_data.get('status'),
            attorney_data.get('admission_date'),
            attorney_data.get('firm_name'),
            attorney_data.get('city'),
            attorney_data.get('county'),
            attorney_data.get('address'),
            attorney_data.get('email'),
            attorney_data.get('phone'),
            attorney_data.get('website'),
            attorney_data.get('law_school'),
            attorney_data.get('graduation_year'),
        ))
        
        attorney_id = cursor.lastrowid
        
        # Insert practice areas
        practice_areas = attorney_data.get('practice_areas', [])
        for i, area in enumerate(practice_areas):
            if area:
                cursor.execute("""
                    INSERT OR IGNORE INTO practice_areas (attorney_id, practice_area, is_primary)
                    VALUES (?, ?, ?)
                """, (attorney_id, area.strip(), i == 0))
        
        return attorney_id
        
    except Exception as e:
        print(f"Error inserting attorney: {e}")
        return None


def start_scrape_log(conn, state):
    """Start a scrape log entry."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO scrape_logs (state, started_at, status)
        VALUES (?, ?, 'running')
    """, (state, datetime.now().isoformat()))
    conn.commit()
    return cursor.lastrowid


def update_scrape_log(conn, log_id, **kwargs):
    """Update a scrape log entry."""
    cursor = conn.cursor()
    
    set_clauses = []
    values = []
    for key, value in kwargs.items():
        set_clauses.append(f"{key} = ?")
        values.append(value)
    
    values.append(log_id)
    
    cursor.execute(f"""
        UPDATE scrape_logs SET {', '.join(set_clauses)} WHERE id = ?
    """, values)
    conn.commit()


def get_stats(db_path=DATABASE_FILE):
    """Get database statistics."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    stats = {}
    
    # Total attorneys
    cursor.execute("SELECT COUNT(*) FROM attorneys")
    stats['total_attorneys'] = cursor.fetchone()[0]
    
    # By state
    cursor.execute("""
        SELECT state, COUNT(*) as count 
        FROM attorneys 
        GROUP BY state 
        ORDER BY count DESC
    """)
    stats['by_state'] = {row['state']: row['count'] for row in cursor.fetchall()}
    
    # By status
    cursor.execute("""
        SELECT status, COUNT(*) as count 
        FROM attorneys 
        GROUP BY status
    """)
    stats['by_status'] = {row['status'] or 'Unknown': row['count'] for row in cursor.fetchall()}
    
    # Top practice areas
    cursor.execute("""
        SELECT practice_area, COUNT(*) as count 
        FROM practice_areas 
        GROUP BY practice_area 
        ORDER BY count DESC 
        LIMIT 20
    """)
    stats['top_practice_areas'] = {row['practice_area']: row['count'] for row in cursor.fetchall()}
    
    # Top firms
    cursor.execute("""
        SELECT firm_name, COUNT(*) as count 
        FROM attorneys 
        WHERE firm_name IS NOT NULL AND firm_name != ''
        GROUP BY firm_name 
        ORDER BY count DESC 
        LIMIT 20
    """)
    stats['top_firms'] = {row['firm_name']: row['count'] for row in cursor.fetchall()}
    
    conn.close()
    return stats


def search_attorneys(db_path=DATABASE_FILE, **filters):
    """Search attorneys with filters."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    query = """
        SELECT DISTINCT a.* 
        FROM attorneys a
        LEFT JOIN practice_areas pa ON a.id = pa.attorney_id
        WHERE 1=1
    """
    params = []
    
    if filters.get('state'):
        query += " AND a.state = ?"
        params.append(filters['state'])
    
    if filters.get('practice_area'):
        query += " AND pa.practice_area LIKE ?"
        params.append(f"%{filters['practice_area']}%")
    
    if filters.get('city'):
        query += " AND a.city LIKE ?"
        params.append(f"%{filters['city']}%")
    
    if filters.get('firm'):
        query += " AND a.firm_name LIKE ?"
        params.append(f"%{filters['firm']}%")
    
    if filters.get('status'):
        query += " AND a.status = ?"
        params.append(filters['status'])
    
    if filters.get('name'):
        query += " AND (a.full_name LIKE ? OR a.last_name LIKE ?)"
        params.extend([f"%{filters['name']}%", f"%{filters['name']}%"])
    
    query += " ORDER BY a.last_name, a.first_name"
    
    if filters.get('limit'):
        query += f" LIMIT {int(filters['limit'])}"
    
    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return results


def export_to_csv(db_path=DATABASE_FILE, output_file="attorneys_export.csv", **filters):
    """Export attorneys to CSV."""
    import csv
    
    attorneys = search_attorneys(db_path, **filters)
    
    if not attorneys:
        print("No attorneys found matching filters.")
        return
    
    fieldnames = [
        'full_name', 'first_name', 'last_name', 'bar_number', 'state',
        'status', 'admission_date', 'firm_name', 'city', 'address',
        'phone', 'email', 'website', 'law_school'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(attorneys)
    
    print(f"✅ Exported {len(attorneys)} attorneys to {output_file}")


if __name__ == "__main__":
    # Initialize database if run directly
    init_database()
    print("\nDatabase ready. Run scrapers to populate data.")
