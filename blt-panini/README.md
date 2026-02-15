# 🍞 Panini - Banned Apps Visualization

**Panini** is a static web application that visualizes apps banned by different countries around the world. It provides both a list view and an interactive map view to explore censorship data.

This project was extracted from the [OWASP BLT](https://github.com/OWASP-BLT/BLT) project to serve as a standalone visualization suitable for GitHub Pages.

## ✨ Features

- **🌍 Interactive Map View**: Visualize banned apps directly on a global map. Countries with bans are highlighted, and clicking them reveals details.
- **📋 List View**: A clean, responsive list of all banned apps, sortable and filterable.
- **🔍 Smart Search**: Search by country or app name.
  - In **Map View**, searching for a country automatically zooms to and highlights it!
- **lighting Dark Mode**: Fully supported dark mode for comfortable viewing at night.
- **📱 Responsive Design**: Works seamlessly on desktop and mobile devices.

### Live Demo - https://owasp-blt.github.io/Panini/

## 🛠️ Technologies

- **HTML5**
- **Tailwind CSS** (via CDN)
- **Leaflet.js** (for maps)
- **Vanilla JavaScript** (no heavy frameworks)

## 📂 Data

The data is stored in `banned_apps.json` in a structured format, making it easy to update or expand.

## 🤝 Contributing

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

## 📄 License

This project is open source. See the [LICENSE](LICENSE) file for details.
