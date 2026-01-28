
import sys
import os
sys.path.append(os.path.join(os.getcwd()))
from models.entities import Vencimiento, Obligacion
print("Vencimiento attributes:")
print([x for x in dir(Vencimiento) if not x.startswith('_')])
print("Obligacion attributes:")
print([x for x in dir(Obligacion) if not x.startswith('_')])
