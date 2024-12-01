import { ChevronLeft, Menu } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "./ui/dialog";
import { Button } from "./ui/button";
import Link from "next/link";

export default function Header({
  heading,
  href,
}: {
  heading: string;
  href: string;
}) {
  const MenuDialog = () => {
    return (
      <Dialog>
        <DialogTrigger asChild>
          <Button className="rounded-full size-8" variant="ghost">
            <Menu
              className="size-6"
              style={{ width: "1.5rem", height: "1.5rem" }}
            />
          </Button>
        </DialogTrigger>
        <DialogContent className="h-full lg:h-auto">
          <DialogHeader>
            <DialogTitle>Mein Account</DialogTitle>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    );
  };

  return (
    <header className="flex px-4 py-5 shadow-xl z-50">
      <div className="grow w-1/5 flex justify-start items-center  text-orange-500">
        <Link href={href} className="flex items-center">
          <ChevronLeft />
          <svg
            viewBox="0 0 16 16"
            width="1em"
            height="1em"
            role="presentation"
            focusable="false"
            aria-hidden="true"
            className="size-8 fill-orange-500"
          >
            <path d="M14.957 7.743c-.047-.127-.7-1.376-1.913-2.944a.262.262 0 01-.056-.133 25.407 25.407 0 00-.365-2.717.445.445 0 00-.132-.234.42.42 0 00-.238-.11l-1.261-.161a.176.176 0 00-.034 0 .261.261 0 00-.188.08.28.28 0 00-.077.195v.453a.017.017 0 01-.005.012.016.016 0 01-.011.005.016.016 0 01-.01-.004C9.876 1.444 9.024.778 8.12.195a1.085 1.085 0 00-1.247 0C2.527 2.975.134 7.495.041 7.743a.456.456 0 00.05.465.431.431 0 00.234.159l1.253.249a.427.427 0 01.21.14c.056.068.09.151.1.24.01.228.247 5.345.544 6.672.025.095.079.18.154.24.076.06.168.092.263.092h.01c.73-.02 1.4-.032 2.123-.042h.06a.137.137 0 00.099-.043.145.145 0 00.04-.103v-.003c-.028-.447-.092-1.468-.143-2.547 0-.027 0-.06-.004-.088a.283.283 0 00-.128-.221 1.377 1.377 0 01-.465-.48 1.437 1.437 0 01-.192-.65c-.067-1.794-.1-3.868-.004-5.49a.265.265 0 01.081-.175.247.247 0 01.348.007.265.265 0 01.074.178v.02c-.062 1.082-.067 2.361-.045 3.623a.32.32 0 00.091.217.297.297 0 00.213.087.29.29 0 00.21-.095.31.31 0 00.084-.22c-.023-1.27-.017-2.557.046-3.642a.265.265 0 01.078-.183.247.247 0 01.356.007c.046.05.071.117.07.186v.02c-.062 1.077-.066 2.348-.045 3.603.001.082.034.16.09.217a.294.294 0 00.214.088.294.294 0 00.21-.095.316.316 0 00.084-.22c-.022-1.264-.016-2.547.047-3.624a.265.265 0 01.077-.183.247.247 0 01.357.008c.046.05.071.116.07.186v.02c-.09 1.578-.06 3.574 0 5.325v.061c0 .227-.053.451-.155.652-.103.201-.25.374-.431.502a.263.263 0 00-.111.203s-.032.27.083 1.572c.054.57.095.964.113 1.142.005.034.02.064.045.086a.13.13 0 00.088.034H8.488l.71.006a.13.13 0 00.09-.034.14.14 0 00.044-.087c.164-1.562.202-2.44.202-2.44a.158.158 0 00-.039-.1.148.148 0 00-.093-.05l-.864-.122a.289.289 0 01-.155-.071.306.306 0 01-.092-.148.448.448 0 01-.011-.138c.35-5.205 2.007-6.96 2.007-6.96a.5.5 0 01.08-.072.255.255 0 01.306-.005.274.274 0 01.097.127c.013.041.02.083.022.126.143 1.636.073 4.42-.016 6.593-.075 1.844-.165 3.291-.165 3.291a.109.109 0 00.063.1.1.1 0 00.04.008c.47.008.934.017 1.425.03h.009a.422.422 0 00.263-.092.448.448 0 00.154-.24c.298-1.327.532-6.443.545-6.672a.452.452 0 01.1-.24.428.428 0 01.212-.14l1.253-.249a.431.431 0 00.234-.159.458.458 0 00.091-.274.465.465 0 00-.043-.185z"></path>
          </svg>
        </Link>
      </div>
      <h1 className="grow w-3/5 flex items-center justify-center font-semibold">
        {heading}
      </h1>
      <div className="grow w-1/5 flex justify-end items-center">
        <MenuDialog />
      </div>
    </header>
  );
}