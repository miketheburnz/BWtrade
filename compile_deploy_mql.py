import os
import subprocess
import shutil
from utils.logger import setup_logging

logger = setup_logging('compile_deploy.log')

def compile_mql():
    try:
        compile_command = 'MetaEditor.exe /compile:EA/BWtrade.mq5 /log:compile.log'
        result = subprocess.run(compile_command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("MQL files compiled successfully.")
        else:
            logger.error(f"Error compiling MQL files: {result.stderr}")
    except Exception as e:
        logger.error(f"Exception during MQL compilation: {e}")

def deploy_mql():
    try:
        terminal_id = 'D0E8209F77C8CF37AD8BF550E51FF075'  
        deploy_path = os.path.join(os.getenv('APPDATA'), 'MetaQuotes', 'Terminal', terminal_id, 'MQL5', 'Experts')
        os.makedirs(deploy_path, exist_ok=True)
        mql_files = ['EA/BWtrade.ex5', 'EA/sqlite3.mqh']
        for file in mql_files:
            shutil.copy(file, deploy_path)
        logger.info("MQL files deployed successfully.")
    except Exception as e:
        logger.error(f"Exception during MQL deployment: {e}")

if __name__ == "__main__":
    compile_mql()
    deploy_mql()
