# -*- coding: utf-8 -*-
"""
Fabfile for installing teamcity on a debian/ubuntu machine
tested on natty and lenny using postgresql as database
and by default runs with user teamcity @ /opt/teamcity
"""

from fabric.api import *
from fabric.contrib.files import exists, upload_template
from fabric.contrib.console import confirm
from time import sleep



TC_DOWNLOAD_LINK         = "http://download.jetbrains.com/teamcity/TeamCity-6.5.6.tar.gz"
DEFAULT_INSTALL_LOCATION = "/opt/teamcity"
DEFAULT_USER             = "teamcity"

DB_NAME = DEFAULT_USER
DB_USER = DEFAULT_USER
DB_PASSWORD = DEFAULT_USER # Change this, really!

PRE_PACKAGES = (
            'wget',
            'python-software-properties',
            )

POST_PACKAGES = (
            'postgresql',
            'libpq-dev',
            'sun-java6-jre'
            )

PPA          = (
            'ferramroberto/java',
            'pitti/postgresql',
            )

# host settings
try:
    from targets import *
except ImportError:
    pass


##########
# targets
# the following example is a vagrant target.
# create your own targets under targets.py so you don't
# have to modify the source

@task
def vagrant():
    """@target: vagrant -- run commands on a vagrant vm"""
    env.hosts = ['127.0.0.1:2222']
    env.result = local('vagrant ssh_config | grep IdentityFile', capture=True)
    env.key_filename = env.result.split()[1]
    env.user = 'vagrant'
    env.home = "/home/vagrant"

@task
def provision():
    distribution = run('lsb_release -is')
    sudo('apt-get update')
    sudo('apt-get install -qq -y %s' % ' '.join(PRE_PACKAGES))
    if distribution == 'Ubuntu':
        for ppa in PPA:
            sudo('add-apt-repository ppa:%s' % ppa)
    if distribution == 'Debian':
        # have to find out what version
        version = run('lsb_release -cs')
        if version == 'lenny': # TODO: make this work for squeeze too
            sudo("echo 'deb http://ftp.debian.org/debian lenny main contrib non-free' > /etc/apt/sources.list.d/non-free.list")
    sudo('apt-get update')
    sudo('apt-get install -qq -y %s' % ' '.join(POST_PACKAGES))

@task
def create_db(name=DB_NAME, user=DB_USER, password= DB_PASSWORD):
    sudo("echo \"CREATE USER %s WITH PASSWORD '%s' CREATEDB;\" | psql -U postgres" % (user, password), user='postgres',)
    sudo("createdb %s --owner %s " % (name, user), user='postgres')

@task
def install_teamcity(user=DEFAULT_USER, location=DEFAULT_INSTALL_LOCATION):
    """Install teamcity with @user, @location"""

    if not exists(location, use_sudo=True):
        sudo('adduser %s --home %s' % (user, location))

    with cd(location):

        if not exists("%s/TeamCity-6.5.6.tar.gz" % location):
            sudo('wget %s && gunzip -c %s | tar x' % (TC_DOWNLOAD_LINK, TC_DOWNLOAD_LINK.split('/')[-1]), user=user)
        sudo('mkdir -p %s/.BuildServer/lib/jdbc' % location, user=user)
        sudo('mkdir -p %s/.BuildServer/config' % location, user=user)
        if not exists("%s/BuildServer/lib/jdbc/postgresql-9.1-901.jdbc4.jar " % location):
            sudo('wget http://jdbc.postgresql.org/download/postgresql-9.1-901.jdbc4.jar -P %s/.BuildServer/lib/jdbc' % location, user=user)

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



