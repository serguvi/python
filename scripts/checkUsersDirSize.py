import os
import sys
from datetime import datetime as dt


def get_size(start_path):
	total_size = 0
	walk = os.walk(start_path)
	for dirpath, dirnames, filenames in walk:
		for file in filenames:
			fp = os.path.join(dirpath, file)
			total_size += os.path.getsize(fp)
	return total_size


if len(sys.argv) == 1:
	path = "C:/Users"
elif len(sys.argv) == 2:
	hostname = sys.argv[1]
	path = "\\\\"+hostname+"\\c$\\Users"
else:
	print("ERROR!!!Too many parameters entered. Please enter only the hostname.")
	sys.exit(1)

os.chdir(path)
usersList = os.listdir()

for user in usersList:
	if user != 'desktop.ini':
		print(user, round(get_size(path+"/"+user)/1024/1024, 2))
