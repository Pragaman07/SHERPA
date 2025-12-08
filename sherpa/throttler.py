import time
import random

def random_sleep(min_seconds=180, max_seconds=540):
    """
    Sleeps for a random amount of time between min_seconds and max_seconds.
    Default is 3 to 9 minutes.
    """
    sleep_time = random.randint(min_seconds, max_seconds)
    print(f"Throttling: Sleeping for {sleep_time} seconds...")
    time.sleep(sleep_time)

def human_typing_delay(min_seconds=2, max_seconds=5):
    """
    Sleeps for a short duration to mimic human typing/interaction.
    """
    time.sleep(random.uniform(min_seconds, max_seconds))
