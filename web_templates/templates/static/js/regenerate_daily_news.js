// 重新生成日报页面Vue应用
const { createApp, ref, onMounted } = Vue;

const app = createApp({
    setup() {
        const isSuccess = ref(false);
        const currentTime = ref(new Date().toLocaleString('zh-CN'));

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
            // 添加键盘快捷键支持
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
            regenerateDailyNews,
            reloadPage
        };
    }
});

app.mount('#app');