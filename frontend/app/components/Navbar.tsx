import Image from "next/image";

const Navbar = () => {
  return (
    <nav className="w-full h-navbar bg-sophos-blue py-2 px-6 flex items-center">
      {/* Logo and text container */}
      <div className="relative h-5 w-32 mr-6 flex items-center gap-3">
        <Image
          src="/logo/sophos-logo-white.svg"
          alt="Sophos Logo"
          width={120}
          height={20}
          className="h-8 w-auto"
          priority
        />
      </div>
    </nav >
  );
};

export default Navbar;
