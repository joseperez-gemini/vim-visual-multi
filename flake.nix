{
  description = "Vim Visual Multi test environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/8ace53bd4dfcfd4c0d2d83a57e8dea8a9c237da1";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          python3
          python3Packages.pip
          neovim
        ];

        shellHook = ''
          # Create temporary python environment
          export PYTHONPATH=$PWD/.nix-python:$PYTHONPATH
          mkdir -p .nix-python

          # Install Python packages in temporary location if not already present
          if [ ! -d ".nix-python/vimrunner" ]; then
            echo "Installing Python dependencies..."
            pip install --target .nix-python vimrunner pynvim
          fi

          echo "VM test environment ready!"
          echo "Available commands:"
          echo "  ./run_tests                    # Run all tests"
          echo "  ./run_tests example            # Run specific test"
          echo "  ./run_tests --list             # List available tests"
        '';
      };
    };
}