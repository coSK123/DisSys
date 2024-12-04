import Link from "next/link";
import { Button } from "./ui/button";

export default function Hero() {
  return (
    <section className="flex w-full h-96 bg-orange-200 items-center justify-center flex-col space-y-8">
      <h1 className="text-5xl font-bold text-center">
        Döner bestellen. Direkt abholen.
      </h1>
      <Link href="/doener" legacyBehavior>
        <Button className="w-56 h-16 rounded-full text-lg bg-orange-600 hover:bg-orange-700 active:bg-orange-800 font-semibold">
          Jetzt bestellen!
        </Button>
      </Link>
    </section>
  );
}
