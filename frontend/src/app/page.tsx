import Hero from "@/components/Hero";
import TopNavigation from "@/components/TopNavigation";
import { Footprints, ShoppingCart, UserRound } from "lucide-react";

export default function Home() {
  const howToOrder = [
    {
      icon: <ShoppingCart className="size-12 lg:size-24" />,
      title: "Gib deine Bestellung auf",
      description: "Wir suchen den passenden Dönerladen für dich.",
    },
    {
      icon: <UserRound className="size-12 lg:size-24" />,
      title: "Teile uns deine persönlichen Daten mit",
      description: "Der Döner wird nur für dich frisch zubereitet.",
    },
    {
      icon: <Footprints className="size-12 lg:size-24" />,
      title: "Begebe dich zu deinem Dönerladen",
      description: "Der Dönerladen bereitet deinen Döner firsch zu.",
    },
  ];
  return (
    <div>
      <TopNavigation />
      <Hero />
      <section className="grid grid-cols-3 p-8 space-y-4">
        <div className="col-span-3 text-center text-xl font-medium">
          So bestellt du
        </div>
        <h1 className="text-4xl font-bold text-orange-600 col-span-3 text-center pb-10">
          Es ist ganz einfach.
        </h1>
        {howToOrder.map((step) => (
          <div
            className="place-items-center w-full text-orange-600"
            key={step.description}
          >
            {step.icon}
          </div>
        ))}
        {howToOrder.map((step) => (
          <div
            key={step.title}
            className="flex flex-col items-center p-4 text-center justify-center space-y-4"
          >
            <h1 className="text-lg lg:text-2xl font-bold">{step.title}</h1>
            <p>{step.description}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
