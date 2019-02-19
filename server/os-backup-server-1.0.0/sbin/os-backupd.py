#!/usr/bin/python
#-------------------------------------------------------------------------------
# Name:        os-backupd.py
# Purpose:     http  server of os-backup for os-backup client.
# Author:      liufapeng
# Email:       pengfaliu@163.com
# Created:     12/13/2014  d/m/y
# Copyright:   (c) liufapeng 2014
# requirement: python >=2.4,tornado >=3.1.0
# verion : 1.0.0
# Licence:     GPL V2
# -*- coding: UTF-8 -*-
#-------------------------------------------------------------------------------
#global varible

import os as myos

from ConfigParser import ConfigParser
import MySQLdb as mdb

import tornado.httpserver
import tornado.web
import tornado.options
import tornado.ioloop

from tornado.options import define,options

class ParseConfig:
    def __init__(self,configfile='/etc/os-backup/os-backupd.conf'):
        self.conf = configfile
        self.parser = ConfigParser()
        self.parser.read(self.conf)
        self.db = self.parser.items('DB')
        
    def dbinfo(self):
        return dict(self.db)


class opdb:
    def __init__(self,host='127.0.0.1',port=3306,user = 'user',password = 'password',databasename = 'database'):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = databasename
    ##connect mysql
    def connect(self,*sqls):
        db = mdb.connect(self.host,self.user,self.password,self.database)
        cur = db.cursor()
        for sql in sqls:
            try:
                cur.execute(sql)
                db.commit()
            except:
                db.rollback()
        db.close()

    def query(self,*sqls): #only use  query
        db = mdb.connect(self.host,self.user,self.password,self.database)
        cur = db.cursor()
        for sql in sqls:
            cur.execute(sql)
            results = cur.fetchall()
            return results
        db.close()


#web server         
define('port',default=80,help='run  on the given port',type=int)
    
class CountApiHandler(tornado.web.RequestHandler):
    def get(self):
        client_ip=self.get_argument('ip')
        self.write('1')
        conf = ParseConfig()
        data = conf.dbinfo()
        querysql = "select ip from backup_count where ip='%s'" % client_ip
        insertsql = "insert into backup_count (ip) values('%s')" % client_ip
        # count plus 1 when this api was call once
        updatesql = "update backup_count set count= count + 1 where ip='%s'" % client_ip
        db = opdb(host=data['host'], port=data['port'], user=data['user'], 
                 password=data['password'], 
                 databasename=data['dbname'])
        #if some record is exsit , just update count.
        if db.query(querysql):
            db.connect(updatesql)
        else:
            db.connect(insertsql,updatesql)

class BackupInfoHandler(tornado.web.RequestHandler):
    def post(self):
        remote_ip = self.request.remote_ip
        client_ip = self.get_argument('ip')
        client_hostname = self.get_argument('hostname')
        client_backup_state = self.get_argument('backup_state')
        client_is_ok = self.get_argument('is_ok')
        client_backup_file_name = self.get_argument('backupfilename')
        client_backup_file_name_size = self.get_argument('file_size')
        client_backup_dirs = self.get_argument('dirs')
        client_insert_time = self.get_argument('insert_time')
        client_backup_time = self.get_argument('backup_time')
        
        #insert database
        conf = ParseConfig()
        data = conf.dbinfo()
         
        querysql = "select ip from backup_count where ip='%s'" % client_ip
        insertsql = "insert into backup_info (ip,hostname,backup_state,is_ok,backupfilename,file_size,dirs,insert_time,backup_time) values ('%s','%s','%s','%s','%s','%s','%s','%s','%s') " \
        % (client_ip,client_hostname,client_backup_state,client_is_ok,client_backup_file_name,\
        client_backup_file_name_size,client_backup_dirs,client_insert_time,client_backup_time)

        db = opdb(host=data['host'], port=data['port'], user=data['user'], 
                 password=data['password'], 
                 databasename=data['dbname'])
        #if db.query(querysql):
        #    db.connect(updatesql)
        #else:
        db.connect(insertsql)

        #response info 
        self.write('0')
        
if __name__=="__main__":
    tornado.options.parse_command_line()
    app = tornado.web.Application(handlers=[(r'/countapi',CountApiHandler),(r'/backupinfo',BackupInfoHandler)])
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
        
