"use client";

import { OrderItem } from "@/types/Order";
import { useEffect, useState } from "react";
import { Food } from "@/types/Food";
import { Minus, Plus, ShoppingBasket } from "lucide-react";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "./ui/dialog";
import { Button } from "./ui/button";
import Link from "next/link";

export default function OrderContent({ foods }: { foods: Food[] }) {
  const [cart, setCart] = useState<OrderItem[]>([]);
  const [isMounted, setIsMounted] = useState(false); // Track if component is mounted

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (!isMounted) return;
    const data = localStorage.getItem("cart");
    if (data) {
      setCart(JSON.parse(data));
    }
  }, [isMounted]);

  const updateCart = (cart: OrderItem[]) => {
    setCart(cart);
    window.localStorage.setItem("cart", JSON.stringify(cart));
  };

  const formatter = new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
  });

  const FoodDialog = ({ food }: { food: Food }) => {
    const price = formatter.format(food.price);
    const OrderButtons = ({ food }: { food: Food }) => {
      const [quantity, setQuantity] = useState(1);
      const onAddToCart = () => {
        const product = { food: food, quantity: quantity };
        if (cart.length === 0) {
          updateCart([product]);
          return;
        }
        const existing = cart.find(
          (item: OrderItem) => item.food.id === food.id
        );
        if (existing) {
          existing.quantity += quantity;
          updateCart([...cart]);
          return;
        }
        cart.push(product);
        updateCart([...cart]);
      };

      return (
        <div className="flex p-4 justify-around space-x-2">
          <div className="flex justify-between items-center bg-black/[.04] rounded-full space-x-3">
            <Button
              variant="ghost"
              className="p-4 rounded-full size-10 hover:bg-black/[.08]"
              onClick={() => setQuantity((prev) => Math.max(1, prev - 1))}
              disabled={quantity <= 1}
            >
              <Minus style={{ width: "1.5rem", height: "1.5rem" }} />
            </Button>
            <span className="w-[2ch] text-center font-bold text-xl">
              {quantity}
            </span>
            <Button
              variant="ghost"
              className="p-4 rounded-full size-10 hover:bg-black/[.08]"
              onClick={() => setQuantity((prev) => prev + 1)}
            >
              <Plus style={{ width: "1.5rem", height: "1.5rem" }} />
            </Button>
          </div>

          <Button
            className="grow h-full rounded-full bg-orange-600 hover:bg-orange-700 active:bg-orange-800 text-xl font-bold"
            onClick={onAddToCart}
          >
            {formatter.format(food.price * quantity)}
          </Button>
        </div>
      );
    };

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
        <DialogContent className="flex flex-col">
          <DialogHeader className="p-4">
            <DialogTitle className="self-start text-xl">
              {food.name}
            </DialogTitle>
          </DialogHeader>
          <div>
            <p>{food.description}</p>
            <p>{food.price} €</p>
          </div>
          <footer className="fixed bottom-0 w-full">
            <OrderButtons food={food} />
          </footer>
        </DialogContent>
      </Dialog>
    );
  };

  const CartDialog = () => {
    const CheckoutButton = () => {
      if (cart.length === 0) {
        return null;
      }
      const total = cart.reduce(
        (acc: number, item: { food: { price: number }; quantity: number }) =>
          acc + item.food.price * item.quantity,
        0
      );
      const totalFormatted = formatter.format(total);

      return (
        <>
          <ShoppingBasket style={{ width: "1.5rem", height: "1.5rem" }} />
          <h2 className="text-xl font-bold">Warenkorb ({totalFormatted})</h2>
        </>
      );
    };

    return (
      <Dialog>
        <DialogTrigger className="w-full min-h-12 rounded-full bg-orange-600 hover:bg-orange-700 active:bg-orange-800 space-x-1 flex items-center justify-center text-white">
          <DialogClose asChild>
            <CheckoutButton />
          </DialogClose>
        </DialogTrigger>
        <DialogContent className="flex flex-col">
          <DialogHeader className="p-4">
            <DialogTitle>hi</DialogTitle>
          </DialogHeader>
          hi
          <Link href="/order/checkout" legacyBehavior>
            <Button>bezahlen</Button>
          </Link>
        </DialogContent>
      </Dialog>
    );
  };

  return (
    <>
      <section className="flex flex-col px-4 py-2 grow overflow-auto">
        <h2 className="my-4 text-xl font-extrabold">Döner ❤️</h2>
        <ul className="space-y-4">
          {foods.map((food) => (
            <li key={food.id}>
              <FoodDialog food={food} />
            </li>
          ))}
        </ul>
      </section>
      {cart.length > 0 && (
        <div className="sticky bottom-0 rounded-t-lg w-full outline outline-gray-200 outline-1 px-2 pt-2 pb-8">
          <CartDialog />
        </div>
      )}
    </>
  );
}
