import TopBar from "@/components/TopBar";
import VenezuelaMap from "@/components/VenezuelaMap";

export default function MapPage() {
  const maptilerKey = process.env.NEXT_PUBLIC_MAPTILER_KEY ?? "";

  return (
    <div className="map-shell">
      <TopBar />
      <VenezuelaMap maptilerKey={maptilerKey} />
    </div>
  );
}
