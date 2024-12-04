import DoenerUpdates from "@/components/DoenerUpdates";
import Header from "@/components/Header";

export default function DoenerPage() {
  return (
    <div className="flex flex-col h-full">
      <Header heading="Speisekarte" href="/" />

      <DoenerUpdates />
    </div>
  );
}
