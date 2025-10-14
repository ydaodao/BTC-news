import subprocess
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('powershell_utils')

# 项目根目录路径
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def run_powershell_command(command, cwd=None, capture_output=True, timeout=None):
    """
    执行PowerShell命令并返回结果
    
    参数:
        command (str): 要执行的PowerShell命令
        cwd (str, optional): 命令执行的工作目录，默认为None（当前目录）
        capture_output (bool, optional): 是否捕获输出，默认为True
        timeout (int, optional): 命令执行超时时间（秒），默认为None（无超时）
    
    返回:
        dict: 包含执行结果的字典，格式为:
            {
                'success': bool,  # 命令是否成功执行
                'stdout': str,    # 标准输出内容
                'stderr': str,    # 标准错误输出内容
                'returncode': int # 返回码
            }
    """
    try:
        # 如果没有指定工作目录，使用项目根目录
        if cwd is None:
            cwd = PROJECT_ROOT
            
        # 确保工作目录存在
        if not os.path.exists(cwd):
            logger.error(f"指定的工作目录不存在: {cwd}")
            return {
                'success': False,
                'stdout': '',
                'stderr': f'工作目录不存在: {cwd}',
                'returncode': -1
            }
            
        # 构建完整的PowerShell命令
        full_command = ['powershell', '-Command', command]
        
        logger.info(f"执行PowerShell命令: {command}")
        logger.info(f"工作目录: {cwd}")
        
        # 执行命令，使用 UTF-8 编码处理输出
        result = subprocess.run(
            full_command,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            encoding='utf-8',  # 明确指定使用 UTF-8 编码
            errors='replace',  # 对于无法解码的字符，使用替代字符
            timeout=timeout
        )
        
        # 处理结果
        stdout = result.stdout.strip() if result.stdout else ""
        stderr = result.stderr.strip() if result.stderr else ""
        success = result.returncode == 0
        
        if success:
            logger.info("命令执行成功")
            if stdout:
                logger.debug(f"输出: {stdout}")
        else:
            logger.error(f"命令执行失败，返回码: {result.returncode}")
            if stderr:
                logger.error(f"错误: {stderr}")
        
        return {
            'success': success,
            'stdout': stdout,
            'stderr': stderr,
            'returncode': result.returncode
        }
    
    except subprocess.TimeoutExpired:
        logger.error(f"命令执行超时: {command}")
        return {
            'success': False,
            'stdout': '',
            'stderr': '命令执行超时',
            'returncode': -1
        }
    except Exception as e:
        logger.error(f"执行命令时发生错误: {str(e)}")
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }

def get_project_path():
    """
    获取项目根目录的绝对路径
    
    返回:
        str: 项目根目录的绝对路径
    """
    return PROJECT_ROOT

# Git操作的便捷函数
def git_pull(repo_path=None, remote='origin', branch='main'):
    """
    执行git pull命令
    
    参数:
        repo_path (str, optional): Git仓库路径，默认为None（项目根目录）
        remote (str, optional): 远程仓库名称，默认为'origin'
        branch (str, optional): 分支名称，默认为'main'
    
    返回:
        dict: 执行结果
    """
    command = f"git pull {remote} {branch}"
    return run_powershell_command(command, cwd=repo_path)

def git_commit(message, repo_path=None, add_all=True):
    """
    执行git commit命令
    
    参数:
        message (str): 提交信息
        repo_path (str, optional): Git仓库路径，默认为None（当前目录）
        add_all (bool, optional): 是否先执行git add -A，默认为True
    
    返回:
        dict: 执行结果
    """
    results = {}
    repo_path = repo_path or PROJECT_ROOT
    if add_all:
        add_result = run_powershell_command("git add -A", cwd=repo_path)
        results['add'] = add_result
        if not add_result['success']:
            results['success'] = add_result['success']
            return results
    
    # 处理提交信息中的引号，避免命令行解析错误
    escaped_message = message.replace('"', '`"').replace("'", "`'")
    commit_command = f'git commit -m "{escaped_message}"'
    
    commit_result = run_powershell_command(commit_command, cwd=repo_path)
    results['commit'] = commit_result
    
    results['success'] = commit_result['success']
    return results

def git_push(repo_path=None, remote='origin', branch='main'):
    """
    执行git push命令
    
    参数:
        repo_path (str, optional): Git仓库路径，默认为None（当前目录）
        remote (str, optional): 远程仓库名称，默认为'origin'
        branch (str, optional): 分支名称，默认为'main'
    
    返回:
        dict: 执行结果
    """
    command = f"git push {remote} {branch}"
    return run_powershell_command(command, cwd=repo_path)

def git_commit_and_push(message, repo_path=None, add_all=True, remote='origin', branch='main'):
    """
    执行git commit和git push命令
    
    参数:
        message (str): 提交信息
        repo_path (str, optional): Git仓库路径，默认为None（当前目录）
        add_all (bool, optional): 是否先执行git add -A，默认为True
        remote (str, optional): 远程仓库名称，默认为'origin'
        branch (str, optional): 分支名称，默认为'main'
    
    返回:
        dict: 执行结果
    """
    results = git_commit(message, repo_path, add_all)
    if results['success']:
        results.update(git_push(repo_path, remote, branch))
    return results

def git_status(repo_path=None):
    """
    执行git status命令
    
    参数:
        repo_path (str, optional): Git仓库路径，默认为None（当前目录）
    
    返回:
        dict: 执行结果
    """
    return run_powershell_command("git status", cwd=repo_path)

# 示例用法
if __name__ == "__main__":
    # 示例：执行简单的PowerShell命令
    result = run_powershell_command("Get-Date")
    print(f"当前日期时间: {result['stdout']}")
    
    # 示例：执行Git操作
    result = git_pull()
    print(f"git pull 结果: {result}")
    result = git_commit("自动提交更新")
    print(f"git commit 结果: {result}")
    result = git_push()
    print(f"git push 结果: {result}")
    # git_commit("自动提交更新")
    # git_push()