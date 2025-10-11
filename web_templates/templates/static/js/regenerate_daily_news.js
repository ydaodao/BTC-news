// 重新生成日报页面Vue应用
const { createApp, ref, onMounted } = Vue;

const app = createApp({
    setup() {
        const isSuccess = ref(false);
        const currentTime = ref(new Date().toLocaleString('zh-CN'));
        const isMobile = ref(false);

        // 检测是否为移动端设备
        const detectMobile = () => {
            const userAgent = navigator.userAgent.toLowerCase();
            const mobileKeywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone'];
            
            // 检查用户代理字符串
            const isMobileUA = mobileKeywords.some(keyword => userAgent.includes(keyword));
            
            // 检查屏幕宽度
            const isMobileScreen = window.innerWidth <= 768;
            
            // 检查触摸支持
            const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
            
            return isMobileUA || (isMobileScreen && isTouchDevice);
        };

        const regenerateDailyNews = () => {
            // 发送GET请求到服务器
            fetch('/api/main?mode=daily_news', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    isSuccess.value = true;
                } else {
                    alert('重新生成日报失败');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('重新生成日报失败');
            });
        };

        const reloadPage = () => {
            location.reload();
        };

        onMounted(() => {
            // 检测设备类型
            isMobile.value = detectMobile();
            
            // 如果是移动端，自动执行regenerateDailyNews
            if (isMobile.value) {
                console.log('检测到移动端设备，自动执行重新生成日报');
                regenerateDailyNews();
            }
            
            // 添加键盘快捷键支持（主要用于PC端）
            document.addEventListener('keydown', (event) => {
                // F5 或 Ctrl+R 刷新页面
                if (event.key === 'F5' || (event.ctrlKey && event.key === 'r')) {
                    event.preventDefault();
                    reloadPage();
                }
            });
        });

        return {
            isSuccess,
            currentTime,
            isMobile,
            regenerateDailyNews,
            reloadPage
        };
    }
});

app.mount('#app');