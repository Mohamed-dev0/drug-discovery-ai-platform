import { useEffect, useState, useRef } from "react";
import axios from "axios";

const ProteinPocketPipeline = () => {
  // 1. The Hooks
  const [inputId, setInputId] = useState("");
  const [pdbData, setPdbData] = useState("");
  const [isFetchingStructure, setIsFetchingStructure] = useState(false);
  const [isDetectingPockets, setIsDetectingPockets] = useState(false);
  const [error, setError] = useState("");
  const [source, setSource] = useState("");
  const [pockets, setPockets] = useState([]);
  const [selectedID, setSelectedID] = useState("");
  const [hasRunPocketDetection, setHasRunPocketDetection] = useState(false);
  const [activePocketRank, setActivePocketRank] = useState(null);
  const [proteinStyle, setProteinStyle] = useState("cartoon");
  const [colorScheme, setColorScheme] = useState("spectrum");

  // 2. The HTML container (the black div)
  const viewerContainerRef = useRef(null);
  // 3. The JavaScript instance of the 3Dmol viewer
  // This allows us to manipulate the 3Dmol viewer from other useEffects.
  const viewerInstanceRef = useRef(null);

  // --- VIEWER EFFECT No. 1: Load the base protein ---
  // Only runs when the PDB structure changes
  useEffect(() => {
    if (pdbData && viewerContainerRef.current) {
      const config = { backgroundColor: "black" };

      // Clear the reference before creating a new viewer (to avoid overlaps)
      viewerContainerRef.current.innerHTML = "";

      // We create the viewer AND store it in our new ref

      const viewer = window.$3Dmol.createViewer(
        viewerContainerRef.current,
        config
      );
      viewerInstanceRef.current = viewer; // <--- Save here

      viewer.addModel(pdbData, "pdb");
      // Basic style (Transparent cartoon to better see the pockets inside)
      viewer.setStyle({}, { cartoon: { color: "spectrum" } });
      viewer.zoomTo();
      viewer.render();
      viewer.zoom(1.2, 1000);
    }
  }, [pdbData]);

  // --- VIEWER EFFECT No. 2: Manage pockets display ---
  // Runs when you click on a pocket in the list (activePocketRank changes)
  useEffect(() => {
    // 1. Security: We need the viewer and the list of pockets.
    const viewer = viewerInstanceRef.current;
    if (!viewer || pockets.length === 0) return;

    // 2. Cleaning: Remove all previous shapes (spheres)
    // to avoid stacking pocket visualizations.
    viewer.removeAllShapes();

    // 3. If no pocket is selected (the accordion has been closed), stop there.
    if (activePocketRank === null) {
      viewer.render(); // We redraw to apply the cleaning
      return;
    }

    // 4. Find the data for the active pocket using its rank
    const activePocket = pockets.find(
      (p) => p.pocket_rank === activePocketRank
    );

    if (activePocket) {
      console.log("Visualisation de la poche :", activePocket.pocket_name);

      // 5. Draw a sphere in the center of the pocket.
      viewer.addSphere({
        center: {
          x: activePocket.center.x,
          y: activePocket.center.y,
          z: activePocket.center.z,
        },
        radius: 4.0,
        color: "red", // Highly visible color
        alpha: 0.5, // Semi-transparent to see the atoms inside
        wireframe: true, // Wirestyle for a more technical look
      });
    }

    // 7. Final rendering to display the sphere
    viewer.render();
  }, [activePocketRank, pockets]); // Dependencies: if the active rank or list changes

  /// --- VIEWER EFFECT No. 3: Dynamic style update  ---
  useEffect(() => {
    const viewer = viewerInstanceRef.current;
    if (!viewer) return;

    const opacity = activePocketRank !== null ? 0.6 : 1.0;

    const styleOptions =
      colorScheme === "spectrum"
        ? { color: "spectrum", opacity }
        : { colorscheme: colorScheme, opacity };

    viewer.setStyle({}, { [proteinStyle]: styleOptions });
    viewer.render();
  }, [proteinStyle, colorScheme, activePocketRank]);

  // 3. The Actions
  const handleSearch = async () => {
    setIsFetchingStructure(true);
    setError("");
    setPdbData("");
    setSource("");
    setSelectedID("");
    setPockets([]);
    setHasRunPocketDetection(false);
    setActivePocketRank(null);

    const cleanId = inputId.trim().toUpperCase();

    if (!cleanId) {
      setError("Please enter an ID.");
      setIsFetchingStructure(false);
      return;
    }

    try {
      const pdbAPI = `http://127.0.0.1:8000/get_structure?clean_id=${encodeURIComponent(
        cleanId
      )}`;
      const response = await axios.get(pdbAPI);

      if (!response.data || !response.data.pdb) {
        throw new Error("No PDB returned by API");
      }

      setPdbData(response.data.pdb);
      setSource(response.data.source || "");
      setSelectedID(cleanId);
    } catch (err) {
      console.error("Failed to fetch structure:", err);
      setError("Impossible to find the protein.");
    } finally {
      setIsFetchingStructure(false);
    }
  };

  const showPockets = async () => {
    setIsDetectingPockets(true);
    setError("");
    setPockets([]);
    setHasRunPocketDetection(false);
    setActivePocketRank(null);

    try {
      const pocketsAPI = `http://127.0.0.1:8000/run_p2rank?clean_id=${encodeURIComponent(
        selectedID
      )}`;
      const response = await axios.post(pocketsAPI);

      if (!response.data.pockets) {
        throw new Error("No pockets returned by API");
      }

      setPockets(response.data.pockets);
      setHasRunPocketDetection(true);
    } catch (err) {
      console.error("Failed to fetch pockets:", err);
      setError("Impossible to find the pockets.");
    } finally {
      setIsDetectingPockets(false);
    }
  };

  const togglePocket = (rank) => {
    if (activePocketRank === rank) {
      setActivePocketRank(null);
    } else {
      setActivePocketRank(rank);
    }
  };

  return (
    <div className="fixed inset-0 flex flex-col bg-gray-900 text-white">
      {/* HEADER */}
      <header className="bg-gray-900 text-white p-4 shadow-md">
        <h1 className="text-xl font-bold">🧬 DrugDiscovery Pro</h1>
      </header>

      {/* MAIN CONTENT */}
      <div className="flex flex-1 overflow-hidden">
        {/* SIDEBAR */}
        <aside className="w-1/3 min-w-[300px] bg-gray-50 p-6 border-r border-gray-200 overflow-y-auto text-gray-900">
          {/* Search Area */}
          <div className="mb-8 bg-white p-4 rounded-lg shadow-sm border">
            <h2 className="text-sm font-semibold text-gray-500 mb-2">
              TARGET SELECTION
            </h2>
            <div className="flex flex-col gap-2">
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Ex: 1IEP or P00533"
                  className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                  value={inputId}
                  onChange={(e) => setInputId(e.target.value)}
                />
                <button
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 font-medium"
                  disabled={isFetchingStructure}
                  onClick={handleSearch}
                >
                  {isFetchingStructure ? "Search..." : "Go"}
                </button>
              </div>

              <button
                className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 font-medium mt-2 disabled:bg-gray-400"
                disabled={selectedID === "" || isDetectingPockets}
                onClick={showPockets}
              >
                {isDetectingPockets ? "Detecting..." : "Detect pockets"}
              </button>

              {hasRunPocketDetection && pockets.length === 0 && (
                <div className="text-blue-500 text-sm font-bold bg-blue-50 p-2 rounded border border-blue-200 mt-2">
                  0️ Zero pocket found!
                </div>
              )}

              {error && (
                <div className="text-red-500 text-sm font-bold bg-red-50 p-2 rounded border border-red-200 mt-2">
                  ⚠️ {error}
                </div>
              )}
            </div>
          </div>

          {/* Protein information */}
          <div className="mb-8">
            <h3 className="font-bold text-gray-800 mb-2 border-b pb-1">
              Protein Details
            </h3>
            <div className="space-y-2 text-sm">
              <p>
                <span className="text-gray-500">ID:</span>{" "}
                <span className="font-mono bg-gray-200 px-1 rounded">
                  {selectedID || "..."}
                </span>
              </p>
            </div>
          </div>

          {/* Pocket display list */}
          {hasRunPocketDetection && pockets.length > 0 && (
            <div className="bg-white p-4 rounded-lg shadow-sm border mb-8">
              <h3 className="font-bold text-gray-800 mb-4">
                Pockets detected - {pockets.length}
              </h3>

              {/* List of pockets */}
              <ul className="space-y-2 max-h-[400px] overflow-y-auto pr-2">
                {pockets.map((poche) => {
                  const isActive = activePocketRank === poche.pocket_rank;

                  return (
                    <li
                      key={poche.pocket_rank}
                      className="text-sm font-medium text-gray-700"
                    >
                      {/* Main line (clickable) */}
                      <div
                        className={`flex items-center cursor-pointer hover:bg-blue-50 p-2 rounded transition-colors ${
                          isActive
                            ? "font-semibold bg-blue-100 text-blue-800"
                            : "bg-gray-50"
                        }`}
                        onClick={() => togglePocket(poche.pocket_rank)}
                      >
                        {/* Arrow icon */}
                        <span className="mr-2 text-xs text-gray-400">
                          {isActive ? "▼" : "▶"}
                        </span>

                        {/* Contents: Rank, Name, Score */}
                        <span>
                          <span className="font-bold">
                            #{poche.pocket_rank}
                          </span>{" "}
                          {poche.pocket_name.trim()} | Score:{" "}
                          <span className="font-bold text-blue-600">
                            {poche.score.toFixed(1)}
                          </span>
                        </span>
                      </div>

                      {/* Details Area */}
                      {isActive && (
                        <div className="ml-6 mt-1 pl-3 border-l-2 border-blue-200 text-gray-600 space-y-1 bg-gray-50 p-2 rounded-r text-xs">
                          <p>• Surface Points: {poche.surface_points}</p>
                          <p>
                            • Center: x={poche.center.x.toFixed(1)}, y=
                            {poche.center.y.toFixed(1)}, z=
                            {poche.center.z.toFixed(1)}
                          </p>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {/* Controls */}
          <div className="bg-white p-4 rounded-lg shadow-sm border mt-8">
            <h3 className="font-bold text-gray-800 mb-4">
              Visualization Controls
            </h3>

            <div className="mb-4">
              <label className="block text-xs font-bold text-gray-500 uppercase mb-1">
                Style
              </label>
              <select
                className="w-full border p-2 rounded bg-gray-50 text-sm"
                value={proteinStyle}
                onChange={(e) => setProteinStyle(e.target.value)}
              >
                <option value="cartoon">Cartoon </option>
                <option value="stick">Stick </option>
                <option value="sphere">Sphere </option>
                <option value="line">Line </option>
              </select>
            </div>

            <div className="mb-4">
              <label className="block text-xs font-bold text-gray-500 uppercase mb-1">
                Color Scheme
              </label>
              <select
                className="w-full border p-2 rounded bg-gray-50 text-sm"
                value={colorScheme}
                onChange={(e) => setColorScheme(e.target.value)}
              >
                <option value="spectrum">Spectrum </option>
                <option value="chain">Chain </option>
                <option value="ssPyMol">Secondary Structure</option>
                <option value="Jmol">Element (Jmol)</option>
              </select>
            </div>
          </div>
        </aside>

        {/* VIEWER 3D */}
        <main className="flex-1 bg-gray-900 relative">
          <div className="absolute inset-0 bg-black" ref={viewerContainerRef} />

          {/* Overlays */}
          <div className="absolute top-4 right-4 bg-black/50 text-white text-xs p-2 rounded">
            Interactive 3D View
          </div>

          {pdbData && (
            <div className="absolute top-2 left-2 bg-white/80 px-2 py-1 rounded text-xs font-bold text-black">
              Source: {source}
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default ProteinPocketPipeline;
