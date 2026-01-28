import customtkinter
import os

path = os.path.dirname(customtkinter.__file__)
print(f"CTK_PATH={path}")

if os.path.exists(path):
    print("PATH EXISTS")
    print(f"CONTENTS={os.listdir(path)}")
else:
    print("PATH DOES NOT EXIST")
