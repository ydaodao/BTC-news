// 二维码页面交互逻辑

function refreshQRCode() {
    const img = document.querySelector('.qrcode-image');
    const refreshBtn = document.querySelector('.refresh-btn');
    const timestamp = new Date().getTime();
    
    // 保存原始按钮文字
    const originalText = refreshBtn.textContent;
    
    // 修改按钮文字为加载状态
    refreshBtn.textContent = '🔄 加载中...';
    refreshBtn.disabled = true;
    
    // 创建新图片来检测加载完成
    const newImg = new Image();
    
    newImg.onload = function() {
        // 图片加载完成，更新显示
        img.src = newImg.src;
        
        // 恢复按钮状态
        refreshBtn.textContent = originalText;
        refreshBtn.disabled = false;
        
        // 更新时间戳显示
        document.querySelector('.timestamp').textContent = 
            '页面加载时间: ' + new Date().toLocaleString('zh-CN');
    };
    
    newImg.onerror = function() {
        // 加载失败，恢复按钮状态
        refreshBtn.textContent = originalText;
        refreshBtn.disabled = false;
    };
    
    // 开始加载
    newImg.src = '/api/qrcode?t=' + timestamp;
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 每30秒自动刷新二维码
    // setInterval(refreshQRCode, 30000);
    
    // 添加键盘快捷键支持
    document.addEventListener('keydown', function(event) {
        // F5 或 Ctrl+R 刷新页面
        if (event.key === 'F5' || (event.ctrlKey && event.key === 'r')) {
            event.preventDefault();
            location.reload();
        }
        // Ctrl+Q 刷新二维码
        if (event.ctrlKey && event.key === 'q') {
            event.preventDefault();
            refreshQRCode();
        }
    });
    
    // 添加图片加载状态指示
    const img = document.querySelector('.qrcode-image');
    if (img) {
        img.addEventListener('load', function() {
            console.log('二维码加载成功');
        });
        
        img.addEventListener('error', function() {
            console.error('二维码加载失败');
        });
    }
});

// 导出函数供全局使用
window.refreshQRCode = refreshQRCode;