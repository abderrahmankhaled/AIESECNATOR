import pandas as pd
import requests
import time
import urllib.parse
import re

# ==========================================
# ⚙️ CONFIGURATION 
# ==========================================

# 1. The main URL of the public webform (Used to grab the cookie)
FORM_URL = "https://podio.com/webforms/25879454/1936053"

# 2. The hidden API endpoint (Leave 'query=' at the end)
SEARCH_BASE_URL = "https://podio.com/webforms/25879454/1936053/items_search?field_id=238040132&limit=50&query="

# ==========================================

def get_podio_session():
    """Visits Podio silently to grab a fresh session cookie, then preps for API searches."""
    print("🔑 Visiting Podio to grab a fresh session cookie...")
    session = requests.Session()
    
    # Put on the Firefox disguise
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0"
    })
    
    try:
        # Visit the main form to get the 'Visitor Sticker'
        session.get(FORM_URL)
        
        # Now configure the session for the hidden API calls
        session.headers.update({
            "Accept": "application/json",
            "Referer": FORM_URL
        })
        print("   ✅ Cookie secured! Ready to scrape.\n")
        return session
    except Exception as e:
        print(f"   ❌ [NETWORK ERROR] Failed to reach Podio. Check your internet connection. {e}")
        return None

def check_podio(query_string, session):
    """Sends the hidden API request using the active session and returns True if taken, False if clean."""
    if not query_string:
        return False
        
    safe_query = urllib.parse.quote(str(query_string))
    url = f"{SEARCH_BASE_URL}{safe_query}"
    
    try:
        response = session.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                return True 
            return False
        else:
            print(f"   ⚠️ [API ERROR] Podio returned status {response.status_code}. Assuming taken to prevent duplicates.")
            return True 
            
    except Exception as e:
        print(f"   ⚠️ [NETWORK ERROR] {e}. Assuming taken to prevent duplicates.")
        return True 

def main():
    print("🚀 Starting Cross-Reference Protocol...\n")
    
    # 1. Initialize the self-renewing session
    session = get_podio_session()
    if not session:
        return # Kill script if we can't connect to Podio

    # 2. Load data
    try:
        df = pd.read_csv(r'C:\Users\DELL\Documents\AIESEC\result.csv', low_memory=False, encoding='utf-8-sig')
        df.columns = df.columns.str.strip() 
    except FileNotFoundError:
        print("❌ ERROR: Could not find 'result.csv'.")
        return

    if df.empty:
        print("❌ ERROR: Pandas loaded the file, but it has 0 rows inside.")
        return

    unclaimed = []

    # 3. Loop through the rows
    for index, row in df.iterrows():
        original_name = str(row.get('name', '')).strip()
        raw_phone = str(row.get('phone_numbers', '')).strip()
        
        if original_name.lower() == 'nan' or not original_name:
            continue

        print(f"[{index + 1}/{len(df)}] Analyzing: {original_name}")

        # ==========================================
        # 🪓 TRAP 3 & 4 FIX: Language & Delimiter Splitting
        # ==========================================
        names_to_check = [original_name]

        # 1. Alphabet Splitter (Rips English and Arabic apart if mashed together without spaces)
        english_only = re.sub(r'[\u0600-\u06FF]+', '', original_name)
        english_only = re.sub(r'\s+', ' ', english_only).strip()

        arabic_only = re.sub(r'[a-zA-Z]+', '', original_name)
        arabic_only = re.sub(r'\s+', ' ', arabic_only).strip()

        if english_only and english_only != original_name:
            names_to_check.append(english_only)
        if arabic_only and arabic_only != original_name:
            names_to_check.append(arabic_only)

        # 2. Delimiter Guillotine (Only splits hyphens with spaces to protect compound words)
        delimiters = [' - ', ' | ', ',', ' – ', ' — ', '(']
        final_names_to_check = []
        
        for name_part in names_to_check:
            chopped = False
            for d in delimiters:
                if d in name_part:
                    parts = [p.strip() for p in name_part.split(d) if p.strip()]
                    final_names_to_check.extend(parts)
                    chopped = True
                    break 
            if not chopped:
                final_names_to_check.append(name_part)

        # Remove duplicates from our list of variations
        final_names_to_check = list(set(final_names_to_check))

        is_name_taken = False
        for search_name in final_names_to_check:
            search_name = search_name.strip('-|(),–— ')
            
            if len(search_name) < 2: 
                continue
                
            print(f"   ➡️ Checking Name: '{search_name}'")
            time.sleep(1) # Rate limit
            if check_podio(search_name, session):
                print(f"   ❌ [TAKEN] Name '{search_name}' matched in database.\n")
                is_name_taken = True
                break 
                
        if is_name_taken:
            continue

        # ==========================================
        # 📞 TRAP 2 FIX: Multi-Format Phone Checking
        # ==========================================
        is_phone_taken = False
        
        if raw_phone.lower() not in ['nan', 'not provided', 'notprovided'] and raw_phone:
            base_phone = raw_phone.split(',')[0].replace(" ", "").replace("-", "")
            
            core_phone = base_phone.replace("+", "").lstrip("0")
            if core_phone.startswith("20") and len(core_phone) >= 11:
                core_phone = core_phone[2:] 

            phones_to_check = [
                base_phone,           
                f"0{core_phone}",     
                f"+20{core_phone}",   
                core_phone            
            ]
            
            phones_to_check = list(set(phones_to_check))

            for p in phones_to_check:
                if len(p) < 8: 
                    continue
                    
                print(f"   ➡️ Checking Phone: '{p}'")
                time.sleep(1) # Rate limit
                if check_podio(p, session):
                    print(f"   ❌ [TAKEN] Phone format '{p}' matched in database.\n")
                    is_phone_taken = True
                    break 

        if is_phone_taken:
            continue

        # Phase 3: Clean Lead
        print("   ✅ [NEW LEAD] Completely clean. Ready to claim.\n")
        unclaimed.append(row)

    # ==========================================
    # 💾 EXPORT
    # ==========================================
    if unclaimed:
        final_df = pd.DataFrame(unclaimed)
        export_path = r'C:\Users\DELL\Documents\AIESEC\ready_to_claim.csv'
        
        try:
            final_df.to_csv(export_path, index=False, encoding='utf-8-sig')
            print(f"🎯 Execution Complete. Saved {len(unclaimed)} new leads to 'ready_to_claim.csv'.")
        except PermissionError:
            fallback_path = r'C:\Users\DELL\Documents\AIESEC\ready_to_claim_backup.csv'
            final_df.to_csv(fallback_path, index=False, encoding='utf-8-sig')
            print("⚠️ WARNING: 'ready_to_claim.csv' was open in another program and locked.")
            print(f"🎯 Saved your {len(unclaimed)} new leads to 'ready_to_claim_backup.csv' instead.")
            
    else:
        print("💀 Execution Complete. 0 new leads found. All taken.")

if __name__ == "__main__":
    main()
