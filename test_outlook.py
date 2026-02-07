import win32com.client as win32
import pythoncom
import os

def test_outlook():
    print("Testing connection to Outlook...")
    try:
        # 1. Initialize COM
        pythoncom.CoInitialize()
        
        # 2. Try to get active instance
        try:
            outlook = win32.GetActiveObject('Outlook.Application')
            print("✅ Success: Found running Outlook instance.")
        except Exception:
            print("⚠️ Could not find active Outlook. Trying to launch new instance...")
            outlook = win32.Dispatch('Outlook.Application')
            print("✅ Success: Launched new Outlook instance.")

        # 3. Create a test item
        mail = outlook.CreateItem(0)
        mail.Subject = "Test Email from Python Script"
        mail.Body = "If you see this, the connection is working!"
        print("✅ Success: Created email draft object.")
        
        print("\nAttempting to list accounts:")
        for acc in outlook.Session.Accounts:
            print(f" - {acc.SmtpAddress}")
            
        print("\nTest passed! Your Outlook setup is compatible.")
        
    except Exception as e:
        print("\n❌ FAILED.")
        print(f"Error: {e}")
        print("-" * 30)
        print("POSSIBLE CAUSES:")
        print("1. You are using 'New Outlook' (the one with the 'Pre' badge). Python CANNOT control this version.")
        print("   -> Solution: Switch back to 'Classic Outlook' via the toggle in the top right corner.")
        print("2. Outlook and this script are running as different users (Admin vs Normal).")
        print("   -> Solution: Close both. Open both normally.")

if __name__ == "__main__":
    test_outlook()
