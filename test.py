import socket
import sys
import threading
import os
import platform
import stat
import time

listen_ip = "localhost"
listen_port = 21
max_connections = 10
conn_list = []
root_dir = "d:/test"

class conn_thread(threading.Thread):
	def __init__(self, conn):		
		threading.Thread.__init__(self)
		self.conn = conn
		self.running = True
		self.curr_dir = ""
		self.home_dir = root_dir

	def message(self, code, msg):
		msg = str(msg).replace("\r", "")  
		ss = msg.split("\n")  
		if len(ss) > 1:  
			r = (str(code) + "-") + ("\r\n" + str(code) + "-").join(ss[:-1])  
			r += "\r\n" + str(code) + " " + ss[-1] + "\r\n"  
		else:  
			r = str(code) + " " + ss[0] + "\r\n" 
		self.conn.send(r)  
		
	def process(self, command, arg):
		command = command.upper()
		if command == "USER":
			self.message(230, "Identified!")
			self.username = arg  
			self.home_dir = root_dir + "/" + self.username  
			self.curr_dir = "/"
		elif command == "SYST":
			self.message(200, "UNIX")
		elif command == "FEAT":
			features = "211-Features:\r\nSITES\r\nEPRT\r\nEPSV\r\nMDTM\r\nPASV\r\n"\
				"REST STREAM\r\nSIZE\r\nUTF8\r\n211 End\r\n"
			self.conn.send(features)
		elif command == "PWD":
			if self.curr_dir == "":
				self.curr_dir = "/"
			self.message(257, '"' + self.curr_dir + '"')
		elif command == "TYPE":
			self.message(200, "OK")
		elif command == "PASV" or command == "EPSV":
			try:
				self.data_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
				self.data_fd.bind((listen_ip, 0))  
				self.data_fd.listen(1)  
				ip, port = self.data_fd.getsockname()  
				if command == "EPSV":  
					self.message(229, "Entering Extended Passive Mode (|||" + str(port) + "|)")  
				else:  
					ipnum = socket.inet_aton(ip)  
					self.message(227, "Entering Passive Mode (%s,%u,%u)." % (",".join(ip.split(".")), (port>>8&0xff), (port&0xff)))  
			except:  
				self.message(500, "failed to create data socket.")  
		elif command == "LIST" or command == "NLST":
			if arg != "" and arg[0] == "-":	arg = ""
			permission = self.get_dir_permission(arg)
			limite_size = self.get_limite_size(arg)
			local_path = self.get_local_path(arg)

			if not os.path.exists(local_path):
				self.message(550, "failed")
				return
			if not self.ready_connect():
				return

			self.message(150, "ok")		
			for f in os.listdir(local_path):
				if f[0] == ".":
					continue				
				info = ""
				fpath = local_path + "/" + f
				st = os.stat(fpath)
				info = "%s%s%s------- %04u %8s %8s %8lu %s %s\r\n" % (
					"-" if os.path.isfile(fpath) else "d",
					"r" if "read" in permission else "-",
					"w" if "write" in permission else "-",
					1, "0", "0", st[stat.ST_SIZE],
					time.strftime("%b %d  %Y", time.localtime(st[stat.ST_MTIME])),
					f)
				print info
				self.data_fd.send(info)
			self.message(226, "Limit size: " + str(limite_size))
			self.data_fd.close()
			self.data_fd = None
		elif command == "CWD":			
			path = get_local_path(arg)
			self.curr_dir = path
			
	
	def get_dir_permission(self, path):
		return "read,write,modify"
	def get_limite_size(self, path):
		return 0
	def get_local_path(self, path):
		mpath = self.home_dir + "/" + path
		return mpath
	def get_curr_path(self, path):
		pass

	def ready_connect(self):
		if self.data_fd != 0:
			fd = self.data_fd.accept()[0]
			self.data_fd.close()
			self.data_fd = fd
			return True
		else:
			return False
		
		
		
		
		
		
		
		
		
		
			
			
			
			
			
			
		
		
		

	def run(self):
		try:  
			if len(conn_list) > 10:  
				self.message(500, "too many connections!")  
				self.conn.close()
				return  
			# Welcome Message 
			self.message(220, "welcome to zhangyangjing's server")  

			# Command Loop  
			line = ""
			while self.running:  
				data = self.conn.recv(4096)
				if len(data) == 0: break
				line += data  
				if line[-2:] != "\r\n": continue  
				line = line[:-2]  
				space = line.find(" ")
				if space == -1:				
					self.process(line, "")
				else:
					self.process(line[:space], line[space+1:])
				line = ""
				 
		except:  
			print "error", sys.exc_info()
		self.conn.close()  
		print "connection end", self.conn
		
	


def main():
	listen_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	listen_fd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	listen_fd.bind((listen_ip, listen_port))
	listen_fd.listen(1024)
	conn_lock = threading.Lock()
	print "begin listening on", listen_ip + ":" + str(listen_port)

	while True:
		conn_fd, remote_addr = listen_fd.accept()
		conn_list.append(conn_fd)
		#print "accepted:",remote_addr,"count of conn:",len(conn_list)
		thd = conn_thread(conn_fd)
		thd.start()



	

if __name__ == '__main__':
	main()

