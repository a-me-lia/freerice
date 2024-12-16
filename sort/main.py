import threading
import time
from typing import List

def sleepsort(arr: List[int]) -> List[int]:
    result = []
    
    def add_after_sleep(x):
        time.sleep(x) 
        result.append(x)

    threads = []
    for x in arr:
        thread = threading.Thread(target=add_after_sleep, args=(x,))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    
    return result

if __name__ == "__main__":
    test_array = [4, 1, 3000, 20, 7, 5, 6]
    print("Original array:", test_array)
    sorted_array = sleepsort(test_array)
    print("Sorted array:", sorted_array)
