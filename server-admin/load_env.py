# load_env.py
import os
import shutil
import importlib.util
import subprocess
import stat
import pwd
import grp
from dotenv import load_dotenv
from collections import OrderedDict

def get_git_branch():
    try:
        # Run 'git rev-parse --abbrev-ref HEAD' to get the current branch name
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).strip().decode('utf-8')
        return branch
    except subprocess.CalledProcessError:
        return None

def update_entrypoints(entrypoints_path, user, group):
    uid = pwd.getpwnam(user).pw_uid
    gid = grp.getgrnam(group).gr_gid

    # Define the path for the permitted subfolder
    permitted_path = os.path.join(entrypoints_path, 'permitted')
    if not os.path.exists(permitted_path):
        os.makedirs(permitted_path)

    # Process all files in the specified directory
    for file in os.listdir(entrypoints_path):
        file_path = os.path.join(entrypoints_path, file)
        
        # Skip directories
        if os.path.isdir(file_path):
            continue
        
        permitted_file_path = os.path.join(permitted_path, file)

        try:
            shutil.copy2(file_path, permitted_file_path)
            subprocess.run(['sed', '-i', 's/\r$//g', permitted_file_path], check=True)
            os.chmod(permitted_file_path, os.stat(permitted_file_path).st_mode | stat.S_IEXEC)
            os.chown(permitted_file_path, uid, gid)
            
        except PermissionError as e:
            print(f"PermissionError: {e} - file_path: {file_path}")
        except Exception as e:
            print(f"Error: {e} - file_path: {file_path}")

def load_template(template_path):
    if not os.path.isfile(template_path):
        raise FileNotFoundError(f"Template file {template_path} does not exist.")
    
    spec = importlib.util.spec_from_file_location("env_template", template_path)
    env_template = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(env_template)
    return env_template.ENV_VARS

def apply_context_overrides(template_vars, context):    
    context_vars = template_vars.get('base', {}).copy()
    context_vars.update(template_vars.get('sites', {}).get(context, {}))
    context_vars['BASE_DIR'] = os.getcwd()
    context_vars['ENV_CONTEXT'] = context 
    context_vars['BRANCH'] = get_git_branch()
    context_vars['POSTGRES_USER'] = context_vars['DB_USER']
    context_vars['POSTGRES_PASSWORD'] = context_vars['DB_PASSWORD']
    context_vars['POSTGRES_DB'] = context_vars['DB_NAME']
    context_vars['CELERY_BROKER_URL'] = f"redis://redis:6379/0"
    return OrderedDict(sorted(context_vars.items()))

def write_env_file(env_vars, output_path):
    with open(output_path, 'w') as file:
        for key, value in env_vars.items():
            file.write(f'{key}={value}\n')

def write_python_file(env_vars, output_path):
    with open(output_path, 'w') as file:
        file.write("# This file is auto-generated from .env\n\n")
        for key, value in env_vars.items():
            if value.isdigit():
                file.write(f"{key} = {value}\n")
            elif value.lower() in ['true', 'false']:
                file.write(f"{key} = {value.capitalize()}\n")
            else:
                file.write(f"{key} = '{value}'\n")

def load_environment(context='default', 
        template_path='env_template.py', 
        output_path='../.env/.env',
        compose_template_path='../compose/docker-compose-template.yml',
        compose_output_path='../docker-compose-autocontext.yml',
        hba_template_path='../compose/pg_hba-template.conf',
        hba_output_path='../compose/pg_hba.conf',
        entrypoints_path='../entrypoints',
        python_output_path='../whg/local_settings_autocontext.py',
        nginx_template_path='nginx_template.conf',
        nginx_output_path='/etc/nginx/sites-available/'
        ):
    # Ensure paths are relative to the script's directory
    script_dir = os.path.dirname(__file__)
    template_path = os.path.join(script_dir, template_path)
    output_path = os.path.join(script_dir, output_path)
    compose_template_path = os.path.join(script_dir, compose_template_path)
    compose_output_path = os.path.join(script_dir, compose_output_path)
    hba_template_path = os.path.join(script_dir, hba_template_path)
    hba_output_path = os.path.join(script_dir, hba_output_path)
    entrypoints_path = os.path.join(script_dir, entrypoints_path)    
    python_output_path = os.path.join(script_dir, python_output_path)
    nginx_template_path = os.path.join(script_dir, nginx_template_path)
    nginx_output_path = os.path.join(script_dir, nginx_output_path)
    
    # Generate environment variable file
    try:
        template_vars = load_template(template_path)
    except FileNotFoundError as e:
        print(e)
        return
    
    env_vars = apply_context_overrides(template_vars, context)
    write_env_file(env_vars, output_path)
    load_dotenv(output_path)
    
    # Generate Docker Compose file
    try:
        with open(compose_template_path, 'r') as file:
            template_content = file.read()
    except FileNotFoundError as e:
        print(f"Compose template file not found: {e}")
        return
    for key, value in env_vars.items():
        template_content = template_content.replace(f"${{{key}}}", value)
    with open(compose_output_path, 'w') as file:
        file.write(template_content)
    
    # Generate PostGres Authentication file
    try:
        with open(hba_template_path, 'r') as file:
            template_content = file.read()
    except FileNotFoundError as e:
        print(f"Compose template file not found: {e}")
        return
    for key, value in env_vars.items():
        template_content = template_content.replace(f"${{{key}}}", value)
    with open(hba_output_path, 'w') as file:
        file.write(template_content)

    # Generate NGINX Configuration
    try:
        with open(nginx_template_path, 'r') as file:
            template_content = file.read()
    except FileNotFoundError as e:
        print(f"NGINX template file not found: {e}")
        return
    for key, value in env_vars.items():
        template_content = template_content.replace(f"${{{key}}}", value)
    nginx_output_full_path = os.path.join(nginx_output_path, env_vars.get('NGINX_SERVER_NAME'))
    with open(nginx_output_full_path, 'w') as file:
        file.write(template_content)
        
    update_entrypoints(entrypoints_path, 'whgadmin', 'root')
    write_python_file(env_vars, python_output_path)

if __name__ == "__main__":
    context = os.path.basename(os.getcwd())
    load_environment(context)
    
    print(f"Context '{context}': environment variables loaded, and written to `.env`, `docker-compose.yml`, and nginx configuration. Entrypoint permissions fixed.")
