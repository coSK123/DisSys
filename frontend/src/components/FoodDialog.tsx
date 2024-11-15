import { Food } from "@/types/Food";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "./ui/dialog";
import { Plus } from "lucide-react";
import OrderButtons from "./OrderButtons";
import { OrderItem } from "@/types/Order";

export default function FoodDialog({
  food,
  cart,
  updateCart,
}: {
  food: Food;
  cart: OrderItem[];
  updateCart: (cart: OrderItem[]) => void;
}) {
  const formatter = new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
  });

  const price = formatter.format(food.price);
  return (
    <Dialog>
      <DialogTrigger asChild>
        <div className="w-full py-3 pl-3 pr-14 flex rounded-lg outline outline-1 outline-gray-300 relative active:[&:not(:has(.child:hover))]:bg-black/[.08] bg-transparent hover:cursor-pointer hover:[&:not(:has(.child:hover))]:bg-black/[.04]">
          <div className="flex flex-col space-y-1">
            <h2 className="font-extrabold">{food.name}</h2>
            <div className="font-">{food.description}</div>
            <h3 className="font-extrabold">{price}</h3>
          </div>
          <div className="child flex items-center justify-center absolute right-3 top-3 outline outline-gray-300 outline-1 rounded-full hover:bg-black/[.04] active:bg-black/[.08] hover:cursor-pointer size-8">
            <Plus className="text-orange-500 size-5" />
          </div>
        </div>
      </DialogTrigger>
      <DialogContent className="h-full sm:h-4/5 flex flex-col p-0">
        <DialogHeader className="p-4">
          <DialogTitle className="self-start text-xl">{food.name}</DialogTitle>
        </DialogHeader>
        <div>
          <p>{food.description}</p>
          <p>{food.price} €</p>
        </div>
        <footer className="fixed bottom-0 w-full">
          <OrderButtons food={food} cart={cart} updateCart={updateCart} />
        </footer>
      </DialogContent>
    </Dialog>
  );
}
