import shutil
import os

source = r"c:\Users\INDIA TECHNOLOGY\beanbyte-coffee-shop\beanbyte.db"
# Aapke Desktop ka rasta
desktop_path = os.path.join(os.environ['USERPROFILE'], "Desktop")
destination = os.path.join(desktop_path, "beanbyte_backup.db")

try:
    shutil.copy2(source, destination)
    print(f"✅ Success! File aapke Desktop par copy ho gayi hai: {destination}")
    print("Ab aap Desktop par jakar 'beanbyte_backup.db' file ko aaram se upload kar sakte hain.")
except Exception as e:
    print(f"❌ Error: {e}")