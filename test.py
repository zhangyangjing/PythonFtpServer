#!/usr/bin/env python  

# -*- coding: utf-8 -*-
#
#    PythonFtpServer
#        @Yangjing Zhang
#            zhangyangjing at gmail dot com (author)
#        @Guilherme Martins
#            ggmartins at gmail dot com (contrib)
#

import os
import platform
import socket
import stat
import sys
import threading
import time

listen_ip = "localhost"
listen_port = 21
max_connections = 10
time_out = 100;
conn_list = []

root_dir = os.path.abspath(os.path.dirname(__file__))
ftp_type = "I"

class conn_thread(threading.Thread):
    
    def __init__(self, conn):
        threading.Thread.__init__(self)
        self.conn = conn
        self.running = True
        self.working_dir = "/"  #this variable must be end with '/'
        self.data_fd = None
        self.alive_time = time.time()
        self.tmpfile=""
        self.commands = {
                'USER'  :   self.cmd_user,  #USER NAME
                'FEAT'  :   self.cmd_feat,
                'PWD'   :   self.cmd_pwd,   #PRINT WORKING DIRECTORY
                'CWD'   :   self.cmd_cwd,   #CHANGE WORKING DIRECTORY
                'MKD'   :   self.cmd_mkd,   #MAKE DIRECTORY
                'RMD'   :   self.cmd_rmd,   #REMOVE DIRECTORY
                'CDUP'  :   self.cmd_cdup,  #CHANGE TO PARENT DIRECTORY
                'TYPE'  :   self.cmd_type,  #REPRESENTATION TYPE
                'PASV'  :   self.cmd_pasv,
                'EPSV'  :   self.cmd_epsv,  #PASSIVE
                'LIST'  :   self.cmd_list,  #LIST
                'NLST'  :   self.cmd_list,  #NAME LIST
                'SYST'  :   self.cmd_syst,  #SYSTEM 
                'RETR'  :   self.cmd_retr,  #RETRIEVE
                'STOR'  :   self.cmd_store,
                'APPE'  :   self.cmd_appe,
                'SIZE'  :   self.cmd_size,
                'SITE'  :   self.cmd_site,
                'RNFR'  :   self.cmd_rnfr,
                'RNTO'  :   self.cmd_rnto,
                'DELE'  :   self.cmd_dele
                }
        
    def run(self):
        self.message(220, "welcome to zhangyangjing's server")
        try:             
            line = ""
            while self.running:
                self.alive_time = time.time()
                data = self.conn.recv(4096).decode()
                if len(data) == 0: break
                line += data
                if line[-2:] != "\r\n": continue
                line = line[:-2]  
                space = line.find(" ")
                if space == -1:                
                    #self.process(line, "")
                    self.commands[line.upper()]("")
                else:
                    #self.process(line[:space], line[space+1:])
                    self.commands[str(line[:space]).upper()](line[space + 1:])
                print(" ->",line)
                line = ""                 
        except:  
            print("error", sys.exc_info())
        self.conn.close()  
        print("connection end", self.conn)
        
    def message(self, code, msg):
        msg = str(msg).replace("\r", "")  
        ss = msg.split("\n")  
        if len(ss) > 1:
            r = (str(code) + "-") + ("\r\n" + str(code) + "-").join(ss[:-1])
            r += "\r\n" + str(code) + " " + ss[-1] + "\r\n"
        else:
            r = str(code) + " " + ss[0] + "\r\n" 
        self.conn.send(str(r).encode())
        
    
    def cmd_user(self, arg):
        self.message(230, "Identified!")
        self.username = arg
        self.home_dir = root_dir
        #self.home_dir = root_dir + "/" + self.username
        
    def cmd_syst(self, arg):
        self.message(200, "UNIX")

    def cmd_feat(self, arg):
        features = "211-Features:\r\nSITE\r\nRNFR\r\nRNTO\r\nEPRT\r\nEPSV\r\nMDTM\r\nPASV\r\n"\
                "REST STREAM\r\nSIZE\r\nMKD\r\nDELE\r\nUTF8\r\n211 End\r\n"
        self.conn.send(str(features).encode())
            
    def cmd_pwd(self, arg):
        self.message(257, '"' + self.working_dir + '"')
        
    def cmd_cwd(self, arg):
        print("cwd")
        locdir, workdingdir = self.get_local_path(str(arg))
        print(locdir)
        if(os.path.isdir(locdir)):
            self.working_dir = workdingdir + "/"
            self.message(250, '"' + self.working_dir + '"')
        else:
            self.message(550, "failed")

    def cmd_cdup(self, arg):
        self.cmd_cwd('..')
        
    def cmd_type(self, arg):
        self.message(200, "OK")
        
    def cmd_pasv(self, arg):
        try:
            self.data_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
            self.data_fd.bind((listen_ip, 0))  
            self.data_fd.listen(1)  
            ip, port = self.data_fd.getsockname()  
            ipnum = socket.inet_aton(ip)  
            self.message(227, "Entering Passive Mode (%s,%u,%u)." % (",".join(ip.split(".")), (port >> 8 & 0xff), (port & 0xff)))  
        except:  
            self.message(500, "failed to create data socket.")
    
    def cmd_epsv(self, arg):
        try:
            self.data_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
            self.data_fd.bind((listen_ip, 0))  
            self.data_fd.listen(1)  
            ip, port = self.data_fd.getsockname()
            self.message(229, "Entering Extended Passive Mode (|||" + str(port) + "|)")  
        except:  
            self.message(500, "failed to create data socket.")
                
    def cmd_list(self, arg):
        print("list")
        if arg != "" and arg[0] == "-":    arg = ""
        permission = self.get_dir_permission(arg)
        limite_size = self.get_limite_size(arg)
        local_path, workingpath = self.get_local_path(self.working_dir)

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
            #print(info)
            self.data_fd.send(str(info).encode())
        self.message(226, "Limit size: " + str(limite_size))
        self.data_fd.close()
        self.data_fd = None
        
    def cmd_retr(self, arg):
        locfile,workingdir = self.get_local_path(arg)
        if not os.path.isfile(locfile):
	    self.message(550, "failed: "+arg+" is not a file")
	    return 
        if not self.ready_connect(): return
        self.message(150, "ok")
        f = open(locfile, "rb")
        while self.running:
            data = f.read(8192)
            if len(data) == 0: break
            self.data_fd.send(data)
        f.close()
        self.data_fd.close()
        self.data_fd = 0
        self.message(226, "ok")
        
    def cmd_store(self, arg):
        locfile,workingdir = self.get_local_path(arg)
        if not self.ready_connect(): return
        self.message(150, "ok")
        f = open(locfile, "wb")
        while self.running:
            data = self.data_fd.recv(8192)
            if len(data) == 0: break
            f.write(data)
        f.close()
        self.data_fd.close()
        self.data_fd = 0
        self.message(226, "ok")
    
    def cmd_appe(self, arg):
        locfile,workingdir = self.get_local_path(arg)
        if not os.path.exists(locfile): return 
        if not self.ready_connect(): return
        self.message(150, "ok")
        f = open(locfile, "ab")
        while self.running:
            self.alive_time = time.time()
            data = self.data_fd.recv(8192)
            if len(data) == 0: break
            f.write(data)
        f.close()
        self.data_fd.close()
        self.data_fd = 0
        self.message(226, "ok")

    def cmd_size(self, arg):
        locfile,workingdir = self.get_local_path(arg)
        if not os.path.exists(locfile):
            self.message(550, "failed: "+arg+" does not exist")
            return
        st = os.stat(locfile)
        self.message(213, "%s" % (+st[stat.ST_SIZE]))
           
    def cmd_site(self, arg):
        locfile,workingdir = self.get_local_path(arg)
        # if not os.path.exists(locfile):
        #    self.message(550, "failed: "+arg+" does not exist")
        #    return
        #st = os.stat(locfile)
        self.message(504, "command not implemented for parameter "+arg)

    def cmd_rnfr(self, arg):
        locfile,workingdir = self.get_local_path(arg)
        self.tmpfile=locfile
        if not os.path.exists(locfile):
            self.message(501, "failed: "+arg+" does not exist")
            return
        print("ok, rename from "+locfile)
        self.message(350, "ok, rename from "+locfile)

    def cmd_rnto(self, arg):
        locfile,workingdir = self.get_local_path(arg)
        if os.path.exists(locfile):
            self.message(501, "failed: filename "+arg+" already exists")
            return
        print("ok, rename to "+locfile)
        print("ok, rename from "+self.tmpfile)
        os.rename(self.tmpfile, locfile)
        self.message(250, "ok, rename to "+locfile)

    def cmd_mkd(self, arg):
        locfile,workingdir = self.get_local_path(arg)
        if os.path.exists(locfile):
            self.message(501, "failed: filename or dir "+arg+" already exists")
            return
        os.mkdir(locfile)
        self.message(250, "ok, "+locfile+" created")

    def cmd_dele(self, arg):
        locfile,workingdir = self.get_local_path(arg)
        if not os.path.exists(locfile):
            self.message(501, "failed: filename or dir "+arg+" does not exist")
            return
        if not os.path.isfile(locfile):
            self.message(501, "failed: "+arg+" is a directory")
            return
        os.remove(locfile)
        self.message(250, "ok, "+locfile+" removed")

    def cmd_rmd(self, arg):
        locfile,workingdir = self.get_local_path(arg)
        if not os.path.exists(locfile):
            self.message(501, "failed: filename or dir "+arg+" does not exist")
            return
        if not os.path.isdir(locfile):
            self.message(501, "failed: "+arg+" is a file")
            return
        os.rmdir(locfile)
        self.message(250, "ok, "+locfile+" removed")

    
    def get_dir_permission(self, path):
        return "read,write,modify"
    def get_limite_size(self, path):
        return 0
    def get_local_path(self, path):
        if(path == ".."):
            ss = self.working_dir[:-1].rpartition('/')
            working_path = ss[0]
        else:
            working_path = path if(len(path)>0 and path[0]=='/') else (self.working_dir + path)
        local_path = self.home_dir + working_path
        print("getLocpath:" + path)
        print("    workingpath:" + working_path)
        print("    localpath:" + local_path)
        return local_path, working_path
    def get_curr_path(self, path):
        pass

    def ready_connect(self):
        if self.data_fd != None:
            fd = self.data_fd.accept()[0]
            self.data_fd.close()
            self.data_fd = fd
            return True
        else:
            return False        
        

def main():
    global conn_list
    listen_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_fd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_fd.bind((listen_ip, listen_port))
    listen_fd.listen(1024)
    conn_lock = threading.Lock()
    print("begin listening on", listen_ip + ":" + str(listen_port))
    print("PWD: ",root_dir)
		
    while True:
        conn_fd, remote_addr = listen_fd.accept()
        print "accepted:",remote_addr,"count of conn:",len(conn_list)
        thd = conn_thread(conn_fd)
        conn_list.append(thd)
        thd.start()
        
        cur_time = time.time()
        for conn in conn_list:
            if(cur_time - conn.alive_time > 9999999):
                conn.conn.shut_down(socket.SHUT_RDWR)
                conn.running = False
        conn_list = [conn for conn in conn_list if conn.running]
    

if __name__ == '__main__':
    main()

