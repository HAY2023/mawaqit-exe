# Windows Installer Documentation

This document provides guidance on how to build the Windows installer for the `mawaqit-exe` project.

## Prerequisites
Before you begin, ensure you have the following installed:
- [Visual Studio](https://visualstudio.microsoft.com/) with C++ development tools.
- [WiX Toolset](https://wixtoolset.org/) for creating Windows installers.

## Building the Installer

1. **Clone the Repository**:  
   Open your terminal and run the following command to clone the repository:
   ```sh
   git clone https://github.com/HAY2023/mawaqit-exe.git
   cd mawaqit-exe
   ```

2. **Open the Solution**:  
   Open the `mawaqit-exe.sln` file in Visual Studio.

3. **Build the Project**:  
   In Visual Studio, set your build configuration to `Release` and build the project by selecting `Build > Build Solution` from the menu.

4. **Build the Installer**:  
   - Once the project is built successfully, navigate to the installer project in Solution Explorer.
   - Right-click on the installer project and select `Build`. This action will generate the installer executable.

5. **Locate the Installer**:  
   After the build completes, the installer can be found in the `bin/Release` directory of the installer project.

## Running the Installer
Double-click on the generated installer executable to run it, and follow the on-screen instructions to install the application.

## Additional Resources
- For additional WiX Toolset usage instructions, refer to the [WiX Documentation](https://wixtoolset.org/documentation/).

## Troubleshooting
If you encounter any issues during the build process, please refer to the project’s issue tracker on GitHub or contact the maintainer for assistance.

End of Documentation.