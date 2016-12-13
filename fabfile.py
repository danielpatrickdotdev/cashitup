from fabric.contrib.files import append, exists, sed
from fabric.contrib.console import confirm
from fabric.context_managers import prefix, cd
from fabric.api import env, local, run, sudo, settings, put, prompt
from fabric.network import disconnect_all
from os import path
import random
from getpass import getpass

DATABASE = 'postgres' # OPTIONS ARE CURRENTLY 'sqlite3' and 'postgres'
REPO_NAME = 'cashitup'
REPO_URL = 'git@bitbucket.com:remarkablerocket/' + REPO_NAME + '.git'

def get_site_folder(user, site):
    return path.join('/home', user, 'sites', site)

def get_source_folder(user, site):
    return path.join(get_site_folder(user, site), REPO_NAME)

def get_venv_folder(user, site):
    return path.join(get_source_folder(user, site), '.env')

def get_settings_folder(user, site):
    return path.join(get_source_folder(user, site), REPO_NAME)

def get_settings_path(user, site):
    return path.join(get_settings_folder(user, site), 'settings.py')

def get_database_settings_path(user, site):
    return path.join(get_settings_folder(user, site), 'database_settings.py')

def get_secret_key_path(user, site):
    return path.join(get_settings_folder(user, site), 'secret_key.py')

def get_local_vend_keys_path():
    return path.join(path.dirname(path.abspath(__file__)),
                     REPO_NAME, 'vend_keys.py')

def provision(name):
    """
    Usage:
    $ fab -H [ip address] --user 'root' provision:name=[name]
    """
    # update software
    run('apt-get update')
    run('apt-get upgrade')

    # set up user - should probably check if exists first
    run('adduser {}'.format(name))
    run('usermod -aG sudo {}'.format(name))
    local('ssh-copy-id {0}@{1}'.format(name, env.host))

    # make sure SSH is allowed by firewall - enable TCP while we're at it
    sudo('ufw allow OpenSSH')
    sudo('ufw allow proto tcp from any to any port 80,443')
    sudo('ufw enable')

    # switch user
    disconnect_all()
    env.user = name

    # tighten up SSH security
    sudo("sed -i 's|[#]*PasswordAuthentication yes|PasswordAuthentication no|g' /etc/ssh/sshd_config")
    sudo("sed -i 's|[#]*PermitRootLogin yes|PermitRootLogin no|g' /etc/ssh/sshd_config")
    #sudo("sed -i 's|UsePAM yes|UsePAM no|g' /etc/ssh/sshd_config")
    sudo('service ssh restart')

    # install system-wide programs
    sudo('apt-get install build-essential nginx python3-dev python3-venv git')
    if "postgres" in DATABASE.lower():
        sudo('apt-get install libpq-dev postgresql postgresql-contrib')
    else:
        sudo('apt-get install sqlite3 libsqlite3-dev')

    # output ssh key to be added to github/bitbucket
    run('ssh-keygen')
    run('cat ~/.ssh/id_rsa.pub')
    confirm('Have you added SSH deployment key to git repo?')

    # reboot just in case needed for installations
    with settings(warn_only=True):
        sudo('shutdown -r now')

def deploy(site_name=None, first_run=False):
    """
    Usage:
    $ fab -H [ip/hostname] --user '[username]' deploy:site_name=example.com

    If site_name is not provided, defaults to ip/hostname
    """
    if not site_name:
        site_name = env.host

    configure_folders(site_name)
    copy_latest_source(site_name)
    create_virtualenv(site_name)
    install_pip_requirements(site_name)
    create_database(site_name)
    run_migrations(site_name)
    if first_run:
        create_superuser(site_name)
    update_settings(site_name)
    collect_static_files(site_name)
    setup_gunicorn(site_name)
    setup_nginx(site_name)
    #TODO configure https

def configure_folders(site_name=None):
    """
    Creates project folders where source code and virtualenv sit
    """
    if not site_name:
        site_name = env.host
    site_folder = get_site_folder(env.user, site_name)

    run('mkdir -p {}'.format(site_folder))
    run('mkdir -p {}'.format(path.join(site_folder, 'static')))
    if 'postgres' not in DATABASE.lower():
        run('mkdir -p {}'.format(path.join(site_folder, 'database')))

def copy_latest_source(site_name=None):
    """
    copy source into source_folder
    """
    if not site_name:
        site_name = env.host
    source_folder = get_source_folder(env.user, site_name)

    if exists(path.join(source_folder, '.git')):
        run('cd {} && git fetch'.format(source_folder))
    else:
        run('git clone {0} {1}'.format(REPO_URL, source_folder))
    current_commit = local("git log -n 1 --format=%H", capture=True)
    run('cd {0} && git reset --hard {1}'.format(source_folder, current_commit))

def create_virtualenv(site_name=None):
    """
    create venv in project_folder/.env
    """
    if not site_name:
        site_name = env.host
    source_folder = get_source_folder(env.user, site_name)
    venv_folder = get_venv_folder(env.user, site_name)

    if not exists(path.join(venv_folder, 'bin', 'pip')):
        run('pyvenv {}'.format(venv_folder))

def install_pip_requirements(site_name=None):
    """
    install/update pip requirements
    """
    if not site_name:
        site_name = env.host
    source_folder = get_source_folder(env.user, site_name)
    venv_folder = get_venv_folder(env.user, site_name)

    with cd(source_folder), prefix('source {}/bin/activate'.format(venv_folder)):
        run('pip install --upgrade pip')
        run('pip install -r {}/requirements/production.txt'.format(source_folder))

def create_database(site_name=None):
    """
    creates postgres database if DATABASE set to postgres.
    """
    if "postgres" in DATABASE.lower():

        if not site_name:
            site_name = env.host
        settings_path = get_settings_path(env.user, site_name)
        database_settings_path = get_database_settings_path(env.user, site_name)
        password = getpass("Type a password for Postgres user {0}: ".format(
                                env.user))

        if not exists(database_settings_path):
            append(database_settings_path,
                   "DATABASES = {{\n"
                   "    'default': {{\n"
                   "        'ENGINE': 'django.db.backends.postgresql_psycopg2',\n"
                   "        'NAME': '{0}',\n"
                   "        'USER': '{1}',\n"
                   "        'PASSWORD': '{2}',\n"
                   "        'HOST': 'localhost',\n"
                   "        'PORT': '',\n"
                   "    }}\n"
                   "}}".format(REPO_NAME, env.user, password))
        append(settings_path, '\nfrom .database_settings import DATABASES')
        
        with settings(warn_only=True):
            sudo('psql -c "CREATE USER {0} WITH NOCREATEDB NOCREATEUSER "'
                 '"ENCRYPTED PASSWORD E\'{1}\'"'.format(env.user, password),
                        user='postgres')
        with settings(warn_only=True):
            sudo('psql -c "CREATE DATABASE {0} WITH OWNER {1}"'.format(REPO_NAME,
                        env.user), user='postgres')
        sudo('psql -c "ALTER ROLE {0} SET client_encoding TO \'utf8\'"'.format(
                    env.user), user='postgres')
        sudo('psql -c "ALTER ROLE {0} SET default_transaction_isolation TO '
             '\'read committed\'"'.format(env.user), user='postgres')
        sudo('psql -c "ALTER ROLE {0} SET timezone TO \'UTC\'"'.format(
                    env.user), user='postgres')

def run_migrations(site_name=None):
    """
    migrate changes to models in DB
    """
    if not site_name:
        site_name = env.host
    source_folder = get_source_folder(env.user, site_name)

    with prefix('source {}/.env/bin/activate'.format(source_folder)):
        run('cd {} && python manage.py makemigrations && python '
            'manage.py migrate'.format(source_folder))

def update_settings(site_name=None):
    """
    Updates DEBUG, ALLOWED_HOSTS and SECRET_KEY django settings
    """
    if not site_name:
        site_name = env.host
    settings_path = get_settings_path(env.user, site_name)
    secret_key_path = get_secret_key_path(env.user, site_name)
    settings_folder_path = get_settings_folder(env.user, site_name)
    local_vend_keys_path = get_local_vend_keys_path()

    if not path.exists(local_vend_keys_path):
        vend_key = prompt("Enter vend key:")
        vend_secret = prompt("Enter vend secret:")
        with open(local_vend_keys_path, "a") as vend_keys_file:
            vend_keys_file.write("KEY = '{}'\n".format(vend_key))
            vend_keys_file.write("SECRET = '{}'\n".format(vend_secret))

    sed(settings_path, 'DEBUG = True', 'DEBUG = False')
    sed(settings_path, 'ALLOWED_HOSTS =.*',
            'ALLOWED_HOSTS = ["{}"]'.format(site_name))
    if not exists(secret_key_path):
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        key = ''.join(random.SystemRandom().choice(chars) for _ in range(50))
        append(secret_key_path, "SECRET_KEY = '{}'".format(key))
    append(settings_path, '\nfrom .secret_key import SECRET_KEY')

    put(local_vend_keys_path, settings_folder_path)

def collect_static_files(site_name=None):
    """
    Collects django static files to where nginx can find them
    """
    if not site_name:
        site_name = env.host
    source_folder = get_source_folder(env.user, site_name)
    
    with prefix('source {}/.env/bin/activate'.format(source_folder)):
        run('cd {} && python manage.py collectstatic --noinput'.format(
            source_folder))

def create_superuser(site_name=None):
    if not site_name:
        site_name = env.host
    source_folder = get_source_folder(env.user, site_name)

    with prefix('source {}/.env/bin/activate'.format(source_folder)):
        run('cd {} && python manage.py createsuperuser'.format(
            source_folder))

def setup_gunicorn(site_name=None):
    """
    copy gunicorn config file and start service
    """
    if not site_name:
        site_name = env.host
    source_folder = get_source_folder(env.user, site_name)

    sudo('sed "s/SITENAME/{1}/g" {0}/deploy_tools/gunicorn-systemd'
         '.template.conf | tee /etc/systemd/system/gunicorn.service'.format(
            source_folder, site_name))

    with settings(warn_only=True):
        sudo('systemctl daemon-reload')
        sudo('systemctl start gunicorn')
        sudo('systemctl enable gunicorn')

def setup_nginx(site_name=None):
    """
    copy nginx config file and (re)start service
    """
    if not site_name:
        site_name = env.host
    source_folder = get_source_folder(env.user, site_name)

    sudo('sed "s/SITENAME/{1}/g" {0}/deploy_tools/nginx.template.conf | '
         'tee /etc/nginx/sites-available/{1}'.format(source_folder, site_name))

    if not exists(path.join('/etc/nginx/sites-enabled/{0}'.format(site_name))):
        sudo('ln -s /etc/nginx/sites-available/{0}'
             ' /etc/nginx/sites-enabled/{0}'.format(site_name))

    sudo('systemctl restart nginx')
    sudo("ufw allow 'Nginx Full'")

def configure_https():
    #TODO
    pass
