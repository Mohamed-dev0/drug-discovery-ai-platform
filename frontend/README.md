# 🌐 Drug Discovery Platform - Frontend

This is the React-based user interface for the AI-powered drug discovery platform. It provides an interactive 3D environment to visualize protein structures and ligand-binding pockets.

## 🚀 Overview
The frontend is built with **React** and **Vite**, focusing on high-performance 3D rendering and a clean, laboratory-grade user experience.

### Key Technologies
- **React.js & Vite**: For a fast and modern development workflow.
- **3Dmol.js**: A high-performance JS library for molecular visualization.
- **Tailwind CSS**: For a responsive and professional scientific UI.
- **Axios**: To communicate with the FastAPI bioinformatics microservices.

## 🛠️ Features
- **3D Interactive Viewer**: Rotate, zoom, and inspect protein structures in real-time.
- **Dynamic Overlays**: Display predicted binding pockets as 3D spheres or point clouds.
- **Visual Controls**: Toggle between different molecular representations (Cartoon, Stick, Sphere).
- **Target Search**: Direct integration with PDB and AlphaFold database identifiers.



## 💻 Installation & Setup

### 1. Prerequisites
- **Node.js** (v16.0.0 or higher)
- **npm** 

### 2. Install Dependencies
Navigate to the frontend directory and install the required packages:
```bash
cd frontend
npm install
```

Run the development server
```bash
npm run dev
```
The application will be available at:
```arduino
http://localhost:5173
```

### 🔌 Backend Dependency
This frontend is designed to work with the FastAPI backend located in:
```bash
/microservices/p2rank-service
```
Make sure the backend is running before using the full functionality of the interface.

The frontend communicates with the backend via HTTP requests (e.g. to trigger pocket detection and retrieve results).

### 🧪 Typical Workflow

1. Start the backend service (FastAPI + P2Rank).
2. Start the frontend development server.
3. Enter a protein identifier (PDB ID or UniProt ID).
4. Load the protein structure.
5. Run pocket detection.
6. Inspect predicted binding pockets in the 3D viewer.

### 📁 Project Structure (simplified)
```text
frontend/
├── src/
│   ├── App.jsx
│   ├── ProteinPocketPipeline.jsx
│   └── ...
├── public/
├── index.html
├── package.json
└── vite.config.ts

```

### 📄 License
This frontend module is part of the Drug Discovery AI Platform and is licensed under the MIT License.