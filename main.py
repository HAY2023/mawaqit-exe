import time
import schedule
from mawaqit import Mawaqit # Assuming Mawaqit is the main class2 launch the application

def job():
    print("Launching MAWAQIT application with notifications...")
    mawaqit_app = Mawaqit()
    mawaqit_app.run() # Call method to run the application

# Schedule the job to run at a specific time, for example, every day at 8:00 AM
schedule.every().day.at("08:00").do(job)

while True:
    schedule.run_pending()
    time.sleep(1) # wait for one second
