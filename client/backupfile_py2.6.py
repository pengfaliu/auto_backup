#!/usr/bin/python
#-------------------------------------------------------------------------------
# Name:        backup.py
# Purpose:     backup /etc /home /boot  /root  to storage system.
#              
# Author:      liufapeng
# Email:       pengfaliu@163.com
# Created:     12/11/2014  d/m/y
# Copyright:   (c) liufapeng 2014
#requirement: python >=2.6
# Licence:     GPL V2
# -*- coding: UTF-8 -*-
#-------------------------------------------------------------------------------
#global varible
import os
import time
import ftplib
import subprocess
import getpass  #get user 
import socket
import struct 
import fcntl 
import multiprocessing  #new in python 2.6 
import shutil  #file oporate
import signal

#mail module
import smtplib
from email.mime.text import MIMEText  

#dir define
sourcedir = [r'/etc',r'/home',r'/boot',r'/root']
worktemp = '/tmp/importantfilebackup/'
tmpdir='/tmp'

#time define
today_now = time.strftime('%Y%m%d-%H%M%S')
today = time.strftime('%Y%m%d') 

#define state code
interfacenotexsit = 100
notroot = 101


class sendmail:  
    def __init__(self,host='smtp.jd.local',user='dnsmon',passwd='dnsmonaea97412',postfix='jd.local',sender = 'dnsmon@jd.com'):
        self.mail_host = host
        self.mail_user = user
        self.mail_pass = passwd
        self.mail_postfix = postfix
        self.mail_sender = sender
        
    def send_mail(self,to_list,subject,content):
        me = self.mail_user+"<"+self.mail_user+"@"+self.mail_postfix+">"
        msg = MIMEText(content)
        msg['Subject'] = subject
        msg['From'] = self.mail_sender
        msg['to'] = to_list
        try:
            s = smtplib.SMTP()
            s.connect(self.mail_host)
            s.login(self.mail_user,self.mail_pass)
            s.sendmail(self.mail_sender,to_list,msg.as_string())
            s.close()
            return True
        except Exception,e:
            print str(e)
            return False

class backupftp:
    def __init__(self,HOST,USER,PASS,REMOTEDIR,PORT=21):
        self.HOST=HOST
        self.USER=USER
        self.PASS=PASS 
        self.REMOTEDIR=REMOTEDIR
        self.PORT=PORT
        self.ftp = ftplib.FTP()
        
    def ftplogin(self):
        ftpsocket = self.ftp
        ftpsocket.set_pasv(True)
        ftpsocket.connect(self.HOST,self.PORT)
        ftpsocket.login(self.USER, self.PASS)
        return ftpsocket
    
    def ftplist(self,ftpsocket):
        print ftpsocket.retrlines('LIST')
        
    def upload(self,ftpsocket,filename):
        bufsize = 163840
        file_handler = open(filename,'rb')
        #ftpsocket.storlines("STOR " + filen, )
        ftpsocket.storbinary("STOR %s" % os.path.basename(filename),file_handler, bufsize)
        file_handler.close()
        ftpsocket.quit() 
        print "upload sucessfull."
        
    def download(self,ftpsocket,filename):
        bufsize = 409600
        file_handler = open(filename,'wb')
        ftpsocket.retrbinary("RETR %s" % os.path.basename(filename),file_handler, bufsize)
        file_handler.close()
        ftpsocket.quit()
        print "download over."
    
    def cwd(self,ftpsocket,pathname):
        print "change to %s " % pathname
        ftpsocket.cwd(pathname)
       
        
    def mkd(self,ftpsocket,dirname):
        ftpsocket.mkd(dirname)
        print "directory %s  is  created" % dirname
    
    def rmd(self,ftpsocket,dirname):
        ftpsocket.rmd(dirname)
        print "directory %s is deleted." % dirname
    
    def dir(self,ftpsocket,diranme):
        ftpsocket.dir(dirname)
    
    def pwd(self,ftpsocket,dirname):
        ftpsocket.pwd(dirname)
        
    def nlst(self,ftpsocket,dirname ='/' ):
        return ftpsocket.nlst(dirname)
    
    def dirisexsit(self,ftpsocket,dirname):
        try:
            result = ftpsocket.cwd(dirname)
        except ftplib.error_perm:
            print "%s is not exsit" % dirname
            return False
        else:
            self.cwd(ftpsocket,'/')
            return True
        
def getip(ethname): 
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0X8915, struct.pack('256s', ethname[:15]))[20:24]) 

def ipaddr():
    try:
        ipaddress = getip('eth0')
    except IOError:
        print "%s is not use or up,try %s" % ('eth0','bond1')
        ipaddress = getip('bond1')
    except IOError:
        print "%s also is not use.exit" % 'bond1'
        exit(interfacenotexsit)
    #finally: python 2.4 not support
    return ipaddress + '-'
    
def tarcompress(srcdir):
    backfilename = srcdir.lstrip('/')+'.tar.gz'
    tar_command = "tar czf %s %s" % (backfilename,srcdir)
    #child = subprocess.Popen(tar_command.split(' '),stdout=subprocess.PIPE,stderr=subprocess.PIPE,preexec_fn=lambda:signal.signal(signal.SIGPIPE, signal.SIG_DFL))
    subprocess.call(tar_command.split(' '))
    #p.wait()
    #print p.pid()
    
def persyb(num): #count '%s' number 
    char = ''
    for i in xrange(0,num):
        char =char +'%s '
    return char

def zipcompress(*filenames):
    #get system info
    hostname = socket.gethostname() + '-'
    ipaddress = ipaddr()
   
    #print "parameter : ",filenames[0]
    zipfilename = hostname+ipaddress+today_now+'.zip'
    zipara = list(zipfilename.split()) + filenames[0]
    #print "zipara :", zipara
    formatchars = persyb(len(zipara))
    zip_command = "zip "+ formatchars %  tuple(zipara)
    
    #start zip 
    if os.system(zip_command) == 0:   
        print 'Successful zip to', zipfilename  
    else:  
        print 'zip failed' 
        
def paracompress(backupdirs):
    mypool = multiprocessing.Pool(processes=len(backupdirs))
    for eachdir in backupdirs:
        result =  mypool.apply_async(tarcompress, args=(eachdir,))
    mypool.close()
    mypool.join()
    if result.successful():
        print "compress successfull."
    else:
        print "compress error"
        
if __name__ == '__main__':
    
    #hostinfo
    hostname = socket.gethostname() + '-'
    ipaddress = ipaddr()
    
    #if user is root ,continure to do.else exit.
    if getpass.getuser() == 'root':
        #change to worktmp directory
        if os.path.exists(worktemp):
            os.chdir(worktemp)
            paracompress(sourcedir)
        else: 
            os.mkdir(worktemp)
            os.chdir(worktemp)
            paracompress(sourcedir)
        
        #zip comparess
        zipcompress(os.listdir(worktemp))
        
        #upload to storage
        host = '192.168.129.100'
        port = '21'
        user = 'upload'
        password = 'jdyunwei@upload'
        remotedir = '/'
        zipfilename = hostname+ipaddress+today_now+'.zip'
        backupdirname =  'osconfiguredir'
        
        ftpclient = backupftp(host,user,password,remotedir,port) #in '/' after login
        ftping = ftpclient.ftplogin()
        
        if  ftpclient.dirisexsit(ftping,backupdirname): #backup dir is exist?
            ftpclient.cwd(ftping,backupdirname)
           
            if ftpclient.dirisexsit(ftping,today):   #judge dir of today is exist?
                ftpclient.cwd(ftping,'/'+backupdirname+'/'+today)
                ftpclient.upload(ftping,zipfilename)
            else:
                ftpclient.mkd(ftping,today)
                ftpclient.cwd(ftping,today)
                ftpclient.upload(ftping,zipfilename)
        else:
            print "%s is not exist" % backupdirname
            
        #go to /tmp and delete worktemp 
        os.chdir(tmpdir)
        shutil.rmtree(worktemp)
        #sendmail to backup mail
        mailto = sendmail()
        mailto.send_mail('liufapeng@jd.com', ipaddress+'backup successfull', 'date:'+today_now+
                        '\nbackup files: ' + str(sourcedir)+
                        '\nbackup to ftp: '+host+
                        '\nbackup ftp directory: '+backupdirname+
                        '\nbakcup filename: '+zipfilename)
    else:
        print "not root user,cann't continue,exit!"	
        exit(notroot)
        
