import csv
from pykeepass import create_database
from pykeepass.exceptions import CredentialsError
from getpass import getpass
import os

# Step 1: Build group hierarchy
def build_group_paths(rows):
    id_to_group = {}
    group_paths = {}

    # First pass: collect all groups
    for row in rows:
        group_id = row.get('!group_id')
        group_name = row.get('!group_name')
        group_parent = row.get('!group_parent')

        if group_id and group_name:
            id_to_group[group_id] = {
                'name': group_name,
                'parent': group_parent
            }

    # Second pass: build full paths
    def get_path(gid):
        if gid not in id_to_group:
            return ''
        group = id_to_group[gid]
        parent_path = get_path(group['parent']) if group['parent'] else ''
        return os.path.join(parent_path, group['name']) if parent_path else group['name']

    for gid in id_to_group:
        group_paths[gid] = get_path(gid)

    return group_paths, id_to_group  # Return id_to_group for debugging

# Step 2: Ensure KeePassXC group exists
def ensure_group_path(kp, path: str):
    current_group = kp.root_group
    for part in path.strip("/").split("/"):
        found = next((g for g in current_group.subgroups if g.name == part), None)
        if not found:
            found = kp.add_group(current_group, part)
        current_group = found
    return current_group

# Step 3: Main conversion function
def main():
    csv_file = 'buttercup-export.csv'
    output_kdbx = 'converted_buttercup.kdbx'
    print(f"🔐 Creating new KeePass database: {output_kdbx}")
    master_password = getpass("Enter a new master password for KeePassXC DB: ")

    # Load CSV data
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=',')  # Use comma as delimiter
        rows = list(reader)

    # Debugging CSV reading
    print("CSV Headers:", reader.fieldnames)  # Print CSV headers

    # Debugging group processing
    for row in rows:
        group_id = row.get('!group_id')
        group_name = row.get('!group_name')
        group_parent = row.get('!group_parent')

    # Build group paths
    group_paths, id_to_group = build_group_paths(rows)  # Unpack returned values

    # Create database
    try:
        kp = create_database(output_kdbx, password=master_password)
    except CredentialsError as e:
        print("❌ Error creating KeePass DB:", e)
        return

    for row in rows:
        if row.get('!type') != 'entry':
            continue  # Skip non-entry rows

        title = row.get('title', 'Untitled')
        username = row.get('username', '')
        password = row.get('password', '')
        url = row.get('URL', '')
        notes = row.get('Notes', '')

        group_id = row.get('!group_id', '')
        group_path = group_paths.get(group_id, 'General')

        group = ensure_group_path(kp, group_path)

        # Check for existing entry
        existing_entry = next((e for e in group.entries if e.title == title), None)
        if existing_entry:
            print(f"Entry '{title}' already exists in group '{group_path}'. Skipping.")
            continue

        kp.add_entry(group, title=title, username=username, password=password, url=url, notes=notes)

    kp.save()
    print("Saving KeePass database")  # Debug database saving
    print(f"✅ Done! KeePassXC database saved as: {output_kdbx}")

if __name__ == '__main__':
    main()
