import sys

try:
    with open("run_log_12.txt", "r", encoding="utf-8", errors="replace") as f:
        print(f.read())
except Exception as e:
    print(e)
