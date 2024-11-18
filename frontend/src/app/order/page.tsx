import Header from "@/components/Header";
import OrderContent from "@/components/OrderContent";

const foods = [
  {
    id: 17,
    name: "Döner",
    price: 5.0,
    description: "",
  },
  {
    id: 16,
    name: "Döner",
    price: 5.0,
    description: "",
  },
  {
    id: 156,
    name: "Döner",
    price: 5.0,
    description: "",
  },
  {
    id: 15,
    name: "Döner",
    price: 5.0,
    description: "",
  },
  {
    id: 14,
    name: "Döner",
    price: 5.0,
    description: "",
  },
  {
    id: 13,
    name: "Döner",
    price: 5.0,
    description: "",
  },
  {
    id: 12,
    name: "Döner",
    price: 5.0,
    description: "",
  },
  {
    id: 11,
    name: "Döner",
    price: 5.0,
    description: "",
  },
  {
    id: 1,
    name: "Döner",
    price: 5.0,
    description: "",
  },
  {
    id: 2,
    name: "Lahmacun",
    price: 2.5,
    description: "Lahmacun",
  },
  {
    id: 3,
    name: "Ayran",
    price: 1.0,
    description: "Ayran",
  },
];

export default function OrderPage() {
  return (
    <div className="flex flex-col h-full">
      <Header heading="Speisekarte" href="/" />
      <OrderContent foods={foods} />
    </div>
  );
}
{
  /* <section className="flex flex-col px-4 py-2 grow overflow-auto">
        <h2 className="my-4 text-xl font-extrabold">Döner ❤️</h2>
        <ul className="space-y-4">
          {foods.map((food) => (
            <li key={food.id}>
              <FoodDialog food={food} />
            </li>
          ))}
        </ul>
      </section>
      <CheckoutButton /> */
}
