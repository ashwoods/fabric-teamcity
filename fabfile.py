# -*- coding: utf-8 -*-
"""
Fabfile for installing teamcity on a debian/ubuntu machine
tested on precise, quatal using postgresql as database
and by default runs with user teamcity @ /opt/teamcity
"""

from fabric.api import *
from fabric.contrib.files import exists, upload_template
from fabric.contrib.console import confirm
from time import sleep

import string, random

###
# Settings
# Override these settings in a conf.py file.
TC_DOWNLOAD_LINK         = "http://download.jetbrains.com/teamcity/TeamCity-7.1.tar.gz"
TC_FILE                  = TC_DOWNLOAD_LINK.split('/')[-1]
INSTALL_LOCATION         = "/opt/teamcity"
DEFAULT_USER             = "teamcity"


JDBC_LINK = "http://jdbc.postgresql.org/download/postgresql-9.2-1001.jdbc4.jar"
JDBC_FILE = JDBC_LINK.split('/')[-1]             

DB_NAME = DEFAULT_USER
DB_USER = DEFAULT_USER

DB_PASSWORD = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(10)) 

# Stage one package list (pre-ppa)
PRE_PACKAGES = (
            'wget',
            'python-software-properties',
            'software-properties-common',
            )


# Stage two package list
POST_PACKAGES = (
            'postgresql',
            'libpq-dev',
            )

# Ubuntu PPA's
PPA          = (
            'webupd8team/java',
            'pitti/postgresql',
            )

# try to import conf file if exists
try:
    from conf import *
except ImportError:
    pass


##########
# targets
# the following example is a vagrant target.
# create your own targets (or anything you'd like to override, like passwords,
# under conf.py so you don't have to modify this file

@task
def vagrant():
    """@target: vagrant -- run commands on a vagrant vm"""
    env.hosts = ['127.0.0.1:2222']
    env.result = local('vagrant ssh_config | grep IdentityFile', capture=True)
    env.key_filename = env.result.split()[1]
    env.user = 'vagrant'
    env.home = "/home/vagrant"

######




def provision():
    """Provision the machine with teamcity requirements"""

    
    sudo('apt-get update')
    sudo('apt-get install -qq -y %s' % ' '.join(PRE_PACKAGES))
    
    distribution = run('lsb_release -is')
    if distribution == 'Ubuntu':
        for ppa in PPA:
            sudo('add-apt-repository ppa:%s' % ppa)
    if distribution == 'Debian':
        # have to find out what version
        version = run('lsb_release -cs')
        if version == 'squeeze': # TODO: make this work for squeeze too
            pass #TODO: test for squeeze




        
    sudo('apt-get update')
    sudo('apt-get install -qq -y %s' % ' '.join(POST_PACKAGES))


def install_oracle_java():
    sudo('echo oracle-java7-installer shared/accepted-oracle-license-v1-1 select true | sudo /usr/bin/debconf-set-selections')
    sudo('apt-get install oracle-java7-installer')

def create_db(name=DB_NAME, user=DB_USER, password= DB_PASSWORD):
    """Installs postgresql as teamcity db backend"""

    sudo("echo \"CREATE USER %s WITH PASSWORD '%s' CREATEDB;\" | psql -U postgres" % (user, password), user='postgres',)
    sudo("createdb %s --owner %s " % (name, user), user='postgres')

def install_teamcity(user=DEFAULT_USER, location=INSTALL_LOCATION):
    """Install teamcity with @user, @location"""

    if not exists(location, use_sudo=True):
        sudo('adduser %s --home %s' % (user, location))

    with cd(location):
        if not exists("%s/%s" % (location, TC_FILE)):
            sudo('wget %s && gunzip -c %s | tar x' % (TC_DOWNLOAD_LINK, TC_DOWNLOAD_LINK.split('/')[-1]), user=user)
        sudo('mkdir -p %s/.BuildServer/lib/jdbc' % location, user=user)
        sudo('mkdir -p %s/.BuildServer/config' % location, user=user)
        if not exists("%s/BuildServer/lib/jdbc/%s " % (location, JDBC_FILE)):
            sudo('wget %s -P %s/.BuildServer/lib/jdbc' % (JDBC_LINK, location), user=user)

        upload_template('templates/database.properties',
                        '%s/.BuildServer/config/database.properties' % location,
                        {
                            'database': DB_NAME,
                            'user': DB_USER,
                            'password': DB_PASSWORD,
                            },
                        use_sudo=True,
                        backup=False)

        with settings(warn_only=True):
            create_db()

    sudo("%s/TeamCity/bin/runAll.sh start" % location,  user=DEFAULT_USER)

@task
def deploy():
    """Deploy teamcity to target server"""

    provision()
    create_db()
    install_teamcity()

@task
def start(location=INSTALL_LOCATION):
    """Start the teamcity server"""
    sudo("%s/TeamCity/bin/runAll.sh start" % location,  user=DEFAULT_USER)

@task
def stop(location=INSTALL_LOCATION):
    """Stop the teamcity server"""
    sudo("%s/Teamcity/bin/runAll.sh stop" % location, user=DEFAULT_USER)
