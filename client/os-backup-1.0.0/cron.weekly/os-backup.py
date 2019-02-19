#!/usr/bin/python
#-------------------------------------------------------------------------------
# Name:        os-backup.py
# Purpose:     backup some diretories  to storage system.
#
# Author:      liufapeng
# Email:       liufapeng@jd.com
# Created:     12/11/2014  d/m/y
# Last Modify : 13/12/2014 d/m/y
# Copyright:   (c) liufapeng 2014
# requirement: python >=2.4
# verion : 1.0.1
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
import threading   #for python 2.4
import shutil  #file oporate
#import signal
from sys import exit
from ConfigParser import ConfigParser

import random
import urllib

#mail module
import smtplib
#from email.mime.text import MIMEText #for python 2.6
from email.MIMEText import MIMEText  # for python 2.4

#dir define
#sourcedir = [r'/etc',r'/home',r'/boot',r'/root']
worktemp = '/tmp/importantfilebackup/'
tmpdir='/tmp'

#time define
today_now = time.strftime('%Y%m%d-%H%M%S')
today = time.strftime('%Y%m%d')

#define state code
interfacenotexsit = 100
notroot = 101

#must front
#parser configure file
def parserconf(section,option):
    configfile = '/etc/backup/backup.conf'
    config = ConfigParser()
    config.read(configfile)
    return config.get(section, option)

class httpclient:
    def __init__(self):
        self.host = parserconf('API', 'host')
        self.port = parserconf('API','port')
        self.user = parserconf('API','user')
        self.passwd =  parserconf('API','password')
        
    def getdata(self,client_ip):
        url = "http://%s:%s/countapi?ip=%s" % (self.host,self.port,client_ip)
        client = urllib.urlopen(url)
        result = client.read()
        return result
    
    def senddata(self,**kargs):
        url = "http://%s/backupinfo" % (self.host)
        params = urllib.urlencode(kargs)
        client = urllib.urlopen(url,params)
        result = client.read()
        return result
        
class sendmail:
    def __init__(self,host=parserconf('Mail','tohost'),user=parserconf('Mail','user'),passwd=parserconf('Mail','pass'),
                 postfix=parserconf('Mail','postfix'),sender = parserconf('Mail','sender')):
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



#random wait
class randomwait:
    def __init__(self,t=60):
        self.time = random.randint(1,t)

    def waittime(self):
        time.sleep(self.time)

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
    return ipaddress

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
    threads = len(backupdirs)
    jobs = list()
    for i in range(0, threads):
        thread = threading.Thread(target=tarcompress,args=(backupdirs[i],)) #don't foget comma in args tuple
        jobs.append(thread)

    for eachthread in jobs:
        eachthread.start()

    for eachthread in jobs:
        eachthread.join()


if __name__ == '__main__':
    #send to http server's data
    osbackup_info={}
    finish_tag = ''
    #hostinfo
    hostname = socket.gethostname() + '-'
    ipaddress = ipaddr()
    sourcedir = parserconf('BackupDirs','directory')

    #if user is root ,continure to do.else exit.
    if getpass.getuser() == 'root':
        #change to worktmp directory
        if os.path.exists(worktemp):
            os.chdir(worktemp)
            paracompress(sourcedir.split(','))
        else:
            os.mkdir(worktemp)
            os.chdir(worktemp)
            paracompress(sourcedir.split(','))

        #zip comparess
        zipcompress(os.listdir(worktemp))

        #upload to storage
        zipfilename = hostname+ipaddress+'-'+today_now+'.zip'
        backupdirname =  parserconf('Ftp','ftpdir')
        host = parserconf('Ftp', 'host')
        port = parserconf('Ftp','port')
        user = parserconf('Ftp','user')
        password = parserconf('Ftp','password')
        remotedir = '/'
        
        #random wait
        sleep = randomwait(60)
        sleep.waittime()
        
        ftpclient = backupftp(host,user,password,remotedir,port) #in '/' after login
        ftping = ftpclient.ftplogin()

        if  ftpclient.dirisexsit(ftping,backupdirname): #backup dir is exist?
            ftpclient.cwd(ftping,backupdirname)

            if ftpclient.dirisexsit(ftping,today):   #judge dir of today is exist?
                ftpclient.cwd(ftping,'/'+backupdirname+'/'+today)
                ftpclient.upload(ftping,zipfilename)
                finish_tag = 1
            else:
                ftpclient.mkd(ftping,today)
                ftpclient.cwd(ftping,today)
                ftpclient.upload(ftping,zipfilename)
                finish_tag = 1
        else:
            print "%s is not exist" % backupdirname
        
        #http client
        osbackup_info['ip']=ipaddress
        osbackup_info['hostname']=hostname
        osbackup_info['backup_state']='1'
        osbackup_info['is_ok']=finish_tag
        osbackup_info['backupfilename']=zipfilename
        osbackup_info['file_size']=str(os.path.getsize(worktemp+zipfilename)/1024.0/1024.0)+' MB'
        osbackup_info['dirs']=sourcedir
        osbackup_info['insert_time']=str(time.strftime('%Y%m%d-%H%M%S')) #get time of now
        osbackup_info['backup_time']=today_now
        print osbackup_info
        
        c = httpclient()
        if c.getdata(osbackup_info['ip']):
            c.senddata(ip=osbackup_info['ip'],hostname=osbackup_info['hostname'],backup_state=osbackup_info['backup_state'],
                       is_ok=osbackup_info['is_ok'],backupfilename=osbackup_info['backupfilename'],file_size=osbackup_info['file_size'],
                       dirs=osbackup_info['dirs'],insert_time=osbackup_info['insert_time'],backup_time=osbackup_info['backup_time'])
        else:#send mail if http is error
            print 'http error!'
            to = parserconf ('Mail','to')
            mailto = sendmail()
            mailto.send_mail(to, ipaddress+'http get error','please check it!')
            
        #go to /tmp and delete worktemp
        os.chdir(tmpdir)
        shutil.rmtree(worktemp)

        #sendmail to backup mail if switch on 
        switch = parserconf('Mail', 'switch')
        to = parserconf ('Mail','to')
        if switch:
            mailto = sendmail()
            mailto.send_mail(to, ipaddress+'backup successfull', 'date:'+today_now+
                            '\nbackup files: ' + str(sourcedir)+
                            '\nbackup to ftp: '+host+
                            '\nbackup ftp directory: '+backupdirname+
                            '\nbakcup filename: '+zipfilename)
        else:
            exit(0) #normal exit
    else:
        print "not root user,cann't continue,exit!"
        exit(notroot)
