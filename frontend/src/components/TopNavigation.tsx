import Link from "next/link";
import { Button } from "./ui/button";
import { Store } from "lucide-react";

export default function TopNavigation() {
  const links = [{ href: "/order", name: "Partner werden", icon: <Store /> }];

  const NavLink = ({
    href,
    name,
    icon,
  }: {
    href: string;
    name: string;
    icon: React.ReactNode;
  }) => {
    return (
      <Link href={href} legacyBehavior key={href}>
        <Button
          variant="ghost"
          disabled
          className="rounded-full text-lg font-semibold p-6"
        >
          {icon}
          {name}
        </Button>
      </Link>
    );
  };

  return (
    <header className="flex justify-between items-center px-6 py-4 shadow-xl bg-white z-50 relative">
      <div className="flex items-center space-x-4">
        {/* Placeholder for logo */}
        <Link href="/" className="text-xl font-semibold text-orange-600">
          Dönerando
        </Link>
      </div>
      <nav className="flex space-x-6">{links.map((link) => NavLink(link))}</nav>
    </header>
  );
}
