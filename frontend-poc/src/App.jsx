import React, { useState, useMemo } from "react";
import Fuse from "fuse.js";
import { Search, MapPin, Calendar, ExternalLink, Filter } from "lucide-react";
// In a real app, you'd fetch this from the JSON file URL
import tournamentsData from "./tournaments.json";

const levels = [
  "Alla",
  "A",
  "B",
  "C",
  "D",
  "1",
  "2",
  "3",
  "4",
  "5",
  "6",
  "7",
  "8",
  "9",
  "10",
  "Öppen",
];
const types = ["Alla", "Turnering", "Seriespel", "Clinic", "Vinnarbana"];

function App() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedLevel, setSelectedLevel] = useState("Alla");
  const [selectedType, setSelectedType] = useState("Alla");

  // Configure Fuse.js for fuzzy search
  const fuse = useMemo(() => {
    return new Fuse(tournamentsData, {
      keys: ["title", "club", "city"],
      threshold: 0.3, // Tolerance for typos
    });
  }, []);

  const [hideSPT, setHideSPT] = useState(false);

  // Lidköping Coordinates
  const USER_LAT = 58.5055;
  const USER_LON = 13.1577;

  function getDistance(lat1, lon1, lat2, lon2) {
    if (!lat1 || !lon1 || !lat2 || !lon2) return null;
    const R = 6371; // Radius of the earth in km
    const dLat = deg2rad(lat2 - lat1);
    const dLon = deg2rad(lon2 - lon1);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(deg2rad(lat1)) *
        Math.cos(deg2rad(lat2)) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return Math.round(R * c); // Distance in km
  }

  function deg2rad(deg) {
    return deg * (Math.PI / 180);
  }

  const filteredTournaments = useMemo(() => {
    let results = tournamentsData.map((t) => ({
      ...t,
      distance: getDistance(USER_LAT, USER_LON, t.lat, t.lon),
    }));

    // 1. Fuzzy Search
    if (searchQuery) {
      results = fuse.search(searchQuery).map((result) => result.item);
    }

    // 2. Exact Filters
    if (selectedLevel !== "Alla") {
      results = results.filter((t) => t.level === selectedLevel);
    }
    if (selectedType !== "Alla") {
      results = results.filter((t) => t.type === selectedType);
    }

    // 3. SPT Hide Toggle (Inverted)
    if (hideSPT) {
      results = results.filter(
        (t) =>
          !t.title.includes("SPT") && !t.title.includes("Swedish Padel Tour")
      );
    }

    // Sort by distance if available, otherwise date
    results.sort((a, b) => {
      if (a.distance !== null && b.distance !== null)
        return a.distance - b.distance;
      return 0;
    });

    return results;
  }, [searchQuery, selectedLevel, selectedType, hideSPT, fuse]);

  return (
    <div className="min-h-screen bg-gray-50 p-4 font-sans text-gray-900">
      <header className="max-w-4xl mx-auto mb-8 text-center pt-8">
        <h1 className="text-4xl font-extrabold tracking-tight text-blue-900 mb-2">
          Padel Finder <span className="text-blue-500">Sverige</span>
        </h1>
        <p className="text-gray-500">Hitta tävlingar nära Lidköping.</p>
      </header>

      <main className="max-w-4xl mx-auto">
        {/* Search & Filter Section */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-8">
          <div className="flex flex-col gap-4">
            <div className="flex flex-col md:flex-row gap-4">
              {/* Search Input */}
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
                <input
                  type="text"
                  placeholder="Sök tävling, klubb eller stad..."
                  className="w-full pl-10 pr-4 py-3 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 transition shadow-sm"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>

              {/* Filters */}
              <div className="flex gap-2">
                <select
                  className="px-4 py-3 rounded-lg border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-sm"
                  value={selectedLevel}
                  onChange={(e) => setSelectedLevel(e.target.value)}
                >
                  {levels.map((l) => (
                    <option key={l} value={l}>
                      {l === "Alla" ? "Alla Nivåer" : `Nivå ${l}`}
                    </option>
                  ))}
                </select>

                <select
                  className="px-4 py-3 rounded-lg border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-sm"
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value)}
                >
                  {types.map((t) => (
                    <option key={t} value={t}>
                      {t === "Alla" ? "Alla Typer" : t}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Toggles */}
            <div className="flex items-center gap-2">
              <label className="flex items-center space-x-2 cursor-pointer select-none border px-3 py-1.5 rounded-full hover:bg-gray-50 transition">
                <input
                  type="checkbox"
                  checked={hideSPT}
                  onChange={(e) => setHideSPT(e.target.checked)}
                  className="rounded text-blue-600 focus:ring-blue-500 h-4 w-4"
                />
                <span className="text-sm font-medium text-gray-700">
                  Dölj SPT/Elit (Visa bara lokalt)
                </span>
              </label>
            </div>
          </div>
        </div>

        {/* Results Grid */}
        <div className="grid gap-4 md:grid-cols-1">
          {filteredTournaments.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              Inga events hittades. Prova ändra sökningen.
            </div>
          ) : (
            filteredTournaments.map((tournament) => (
              <TournamentCard key={tournament.id} data={tournament} />
            ))
          )}
        </div>
      </main>
    </div>
  );
}

function TournamentCard({ data }) {
  const badgeColor =
    {
      Turnering: "bg-blue-100 text-blue-700",
      Seriespel: "bg-purple-100 text-purple-700",
      Vinnarbana: "bg-orange-100 text-orange-700",
      Clinic: "bg-green-100 text-green-700",
    }[data.type] || "bg-gray-100 text-gray-700";

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div className="flex-1">
        {/* City Badge - Prominent */}
        <div className="mb-2 flex items-center gap-2">
          <span className="bg-gray-900 text-white px-2.5 py-1 rounded-md text-sm font-bold flex items-center">
            <MapPin size={14} className="mr-1" />
            {data.city}
          </span>
          {data.distance !== null && (
            <span className="text-xs font-semibold text-green-700 bg-green-50 px-2 py-1 rounded-md border border-green-100">
              {data.distance} km bort
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 mb-1">
          <span
            className={`px-2 py-0.5 rounded text-xs font-semibold ${badgeColor}`}
          >
            {data.type}
          </span>
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-gray-100 text-gray-600 border border-gray-200">
            Nivå {data.level}
          </span>
        </div>
        <h3 className="text-lg font-bold text-gray-900 leading-tight mb-2">
          {data.title}
        </h3>

        <div className="flex items-center text-gray-500 text-sm space-x-4">
          <div className="flex items-center">
            <span className="text-gray-400 mr-1">📍</span> {data.club}
          </div>
          <div className="flex items-center">
            <Calendar size={16} className="mr-1" />
            {(() => {
              if (data.date.includes("??")) {
                const [y, m] = data.date.split("-");
                const months = [
                  "",
                  "Januari",
                  "Februari",
                  "Mars",
                  "April",
                  "Maj",
                  "Juni",
                  "Juli",
                  "Augusti",
                  "September",
                  "Oktober",
                  "November",
                  "December",
                ];
                return `${months[parseInt(m)] || m} ${y}`;
              }
              return data.date;
            })()}
          </div>
        </div>
        <div className="mt-2 text-xs text-gray-400 font-medium">
          Hittades på: <span className="text-gray-600">{data.source}</span>
        </div>
      </div>

      <div className="flex flex-col gap-2 w-full sm:w-auto">
        <a
          href={data.url}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2 bg-slate-900 text-white px-5 py-2.5 rounded-lg hover:bg-slate-800 transition text-sm font-medium justify-center"
        >
          Visa Event <ExternalLink className="h-4 w-4" />
        </a>
        {data.lat && (
          <a
            href={`https://www.google.com/maps/search/?api=1&query=${data.lat},${data.lon}`}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 bg-blue-50 text-blue-600 px-5 py-2.5 rounded-lg hover:bg-blue-100 transition text-sm font-medium justify-center border border-blue-100"
          >
            Hitta hit <MapPin className="h-4 w-4" />
          </a>
        )}
      </div>
    </div>
  );
}

export default App;
