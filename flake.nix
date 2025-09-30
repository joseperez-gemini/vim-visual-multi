{
  description = "Vim Visual Multi test environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/d2ed99647a4b195f0bcc440f76edfa10aeb3b743";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};

      vimrunner = pkgs.python3Packages.buildPythonPackage rec {
        pname = "vimrunner";
        version = "1.0.3";

        src = pkgs.fetchPypi {
          inherit pname version;
          sha256 = "0vin1xgrcg6sj65l8zayizdc582mm532ra35mf00r96sc6npvgih";
        };

        doCheck = false;
      };
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          (python3.withPackages (ps: with ps; [
            pynvim
            vimrunner
            pylint
            black
          ]))
          pyright
        ];
      };
    };
}
