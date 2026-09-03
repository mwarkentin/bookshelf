csv := "Book Tracker.csv"
icloud_csv := "/Users/mwarkentin/Library/Mobile Documents/com~apple~CloudDocs/Downloads" / csv

# Copy CSV from iCloud, rebuild index.html, commit and push to main
update: copy build commit push

# Copy the Book Tracker CSV export from iCloud Downloads
copy:
    cp "{{icloud_csv}}" "{{csv}}"

# Regenerate index.html from the CSV export
build:
    uv run generate_bookshelf.py "{{csv}}" -o index.html

# Commit the updated index.html
commit:
    git add index.html
    git commit -m "Update bookshelf"

# Push to main
push:
    git push origin main
