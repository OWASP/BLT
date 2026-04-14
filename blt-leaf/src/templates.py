def get_404_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 - Page Not Found | BLT-Leaf</title>
    <link rel="shortcut icon" href="/favicon.ico" type="image/x-icon">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        window.tailwind = {
            config: {
                darkMode: 'class'
            }
        };

        // Initialize theme immediately to prevent FOUC
        (function () {
            const savedTheme = localStorage.getItem('theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const theme = savedTheme || (prefersDark ? 'dark' : 'light');

            if (theme === 'dark') {
                document.documentElement.classList.add('dark');
            }
        })();
    </script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
    <style>
        .dark body {
            background-color: #0f172a !important;
            color: #f1f5f9 !important;
        }
    </style>
</head>
<body class="flex h-screen flex-col bg-slate-50 text-slate-900 antialiased dark:bg-slate-900 dark:text-slate-100 transition-colors duration-300">
   

    <main class="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <div class="relative mb-8">
            <div class="absolute inset-0 blur-3xl bg-red-500/10 dark:bg-red-500/20 rounded-full"></div>
            <div class="relative">
                <span class="text-9xl font-extrabold text-slate-200 dark:text-slate-800 select-none">404</span>
                <div class="absolute inset-0 flex items-center justify-center">
                    <div class="relative">
                        <i class="fas fa-search text-7xl text-red-600 dark:text-red-500 animate-pulse"></i>
                        <i class="fas fa-leaf absolute bottom-0 right-0 text-3xl text-emerald-500 dark:text-emerald-400 transform rotate-45"></i>
                    </div>
                </div>
            </div>
        </div>

        <h2 class="text-3xl sm:text-4xl font-bold text-slate-900 dark:text-white mb-4">You've wandered off the track</h2>
        <p class="text-slate-600 dark:text-slate-400 max-w-md mb-10 text-lg">
            Oops! This page doesn't exist or has been moved to a different coordinate. Let's get you back on safe grounds.
        </p>

        <div class="flex flex-col sm:flex-row gap-4">
            <a href="/" class="group relative inline-flex items-center justify-center gap-2 rounded-xl bg-red-600 px-8 py-3.5 text-lg font-semibold text-white transition-all hover:bg-red-700 hover:shadow-lg hover:shadow-red-500/25 active:scale-95">
                <i class="fas fa-home transition-transform group-hover:-translate-y-0.5"></i>
                Back to Dashboard
            </a>
            <a href="https://github.com/OWASP-BLT/BLT-Leaf" target="_blank" rel="noopener noreferrer" class="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-8 py-3.5 text-lg font-semibold text-slate-700 transition-all hover:bg-slate-50 hover:border-slate-400 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700 active:scale-95">
                <i class="fab fa-github"></i>
                GitHub
            </a>
        </div>
    </main>

</body>
</html>"""
