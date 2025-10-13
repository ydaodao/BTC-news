// 二维码页面Vue应用
// qrcode.js 中启用 Element Plus
const { createApp, ref, onMounted } = Vue;

const app = createApp({
    setup() {
        const title = ref('微信公众号二维码');
        const qrcodeUrl = ref('/api/qrcode?t=' + new Date().getTime());
        const imageError = ref(false);
        const isLoading = ref(false);
        const currentTime = ref(new Date().toLocaleString('zh-CN'));

        const refreshQRCode = () => {
            isLoading.value = true;
            imageError.value = false;
            
            // 创建新图片来检测加载完成
            const newImg = new Image();
            const timestamp = new Date().getTime();
            
            newImg.onload = () => {
                // 图片加载完成，更新显示
                qrcodeUrl.value = '/api/qrcode?t=' + timestamp;
                isLoading.value = false;
                currentTime.value = new Date().toLocaleString('zh-CN');
            };
            
            newImg.onerror = () => {
                // 加载失败
                isLoading.value = false;
                imageError.value = true;
            };
            
            // 开始加载
            newImg.src = '/api/qrcode?t=' + timestamp;
        };

        const handleImageError = () => {
            imageError.value = true;
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
                
                // R 键刷新二维码
                if (event.key === 'r' || event.key === 'R') {
                    refreshQRCode();
                }
            });
            
            // 可以添加自动刷新功能
            // setInterval(refreshQRCode, 30000);
        });

        return {
            title,
            qrcodeUrl,
            imageError,
            isLoading,
            currentTime,
            refreshQRCode,
            handleImageError,
            reloadPage
        };
    }
});
// 在挂载前启用Element Plus（CDN模式）
app.use(ElementPlus);
app.mount('#app');