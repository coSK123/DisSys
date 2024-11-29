import Link from "next/link";
import { Button } from "./ui/button";

export default function Hero() {
  return (
    <section className="flex w-full h-96 bg-gray-50 items-center justify-center">
      <Link href="/order" legacyBehavior>
        <Button>Los gehts!</Button>
      </Link>
    </section>
  );
}
