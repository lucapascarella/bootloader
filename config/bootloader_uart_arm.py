"""*****************************************************************************
* Copyright (C) 2019 Microchip Technology Inc. and its subsidiaries.
*
* Subject to your compliance with these terms, you may use Microchip software
* and any derivatives exclusively with Microchip products. It is your
* responsibility to comply with third party license terms applicable to your
* use of third party software (including open source software) that may
* accompany Microchip software.
*
* THIS SOFTWARE IS SUPPLIED BY MICROCHIP "AS IS". NO WARRANTIES, WHETHER
* EXPRESS, IMPLIED OR STATUTORY, APPLY TO THIS SOFTWARE, INCLUDING ANY IMPLIED
* WARRANTIES OF NON-INFRINGEMENT, MERCHANTABILITY, AND FITNESS FOR A
* PARTICULAR PURPOSE.
*
* IN NO EVENT WILL MICROCHIP BE LIABLE FOR ANY INDIRECT, SPECIAL, PUNITIVE,
* INCIDENTAL OR CONSEQUENTIAL LOSS, DAMAGE, COST OR EXPENSE OF ANY KIND
* WHATSOEVER RELATED TO THE SOFTWARE, HOWEVER CAUSED, EVEN IF MICROCHIP HAS
* BEEN ADVISED OF THE POSSIBILITY OR THE DAMAGES ARE FORESEEABLE. TO THE
* FULLEST EXTENT ALLOWED BY LAW, MICROCHIP'S TOTAL LIABILITY ON ALL CLAIMS IN
* ANY WAY RELATED TO THIS SOFTWARE WILL NOT EXCEED THE AMOUNT OF FEES, IF ANY,
* THAT YOU HAVE PAID DIRECTLY TO MICROCHIP FOR THIS SOFTWARE.
*****************************************************************************"""
global flashNames

global ram_start
global ram_size

global flash_start
global flash_size
global flash_erase_size

flash_start         = 0
flash_size          = 0
flash_erase_size    = 0

FlashNames          = ["FLASH", "IFLASH"]
RamNames            = ["HSRAM", "HRAMC0", "HMCRAMC0", "IRAM"]

addr_space          = ATDF.getNode("/avr-tools-device-file/devices/device/address-spaces/address-space")
addr_space_children = addr_space.getChildren()

for mem_idx in range(0, len(addr_space_children)):
    mem_seg     = addr_space_children[mem_idx].getAttribute("name")
    mem_type    = addr_space_children[mem_idx].getAttribute("type")

    if ((any(x == mem_seg for x in FlashNames) == True) and (mem_type == "flash")):
        flash_start = int(addr_space_children[mem_idx].getAttribute("start"), 16)
        flash_size  = int(addr_space_children[mem_idx].getAttribute("size"), 16)

    if ((any(x == mem_seg for x in RamNames) == True) and (mem_type == "ram")):
        ram_start   = addr_space_children[mem_idx].getAttribute("start")
        ram_size    = addr_space_children[mem_idx].getAttribute("size")

periphNode          = ATDF.getNode("/avr-tools-device-file/devices/device/peripherals")
peripherals         = periphNode.getChildren()

def setBtlDualBankCommentVisible(symbol, event):
    symbol.setVisible(event["value"])

def calcBootloaderSize():
    global flash_erase_size

    # Calculated values with Optimization level -O1 and nearest BOOTPROT value
    max_uart_btl_size   = 2048
    btl_size            = 0

    if (flash_erase_size != 0):
        if (flash_erase_size >= max_uart_btl_size):
            btl_size = flash_erase_size
        else:
            btl_size = max_uart_btl_size

    return btl_size

def setAppStartAndCommentVisible(symbol, event):
    global flash_start
    global flash_size

    if (event["id"] == "BTL_SIZE"):
        custom_app_start_addr = str(hex(flash_start + int(event["value"],10)))

        Database.setSymbolValue("core", "APP_START_ADDRESS", custom_app_start_addr[2:])
    else:
        comment_enable      = False

        custom_app_start_addr = int(Database.getSymbolValue("core", "APP_START_ADDRESS"), 16)
        btl_size = calcBootloaderSize()

        if (custom_app_start_addr < (flash_start + btl_size)):
            symbol.setLabel("***  WARNING!!! Application Start Address Should be equal to or Greater than Bootloader Size ***")
            comment_enable = True
        elif (custom_app_start_addr >= (flash_start + flash_size)):
            symbol.setLabel("*** WARNING!!! Application Start Address is exceeding the Flash Memory Space ***")
            comment_enable = True

        symbol.setVisible(comment_enable)

def setBootloaderSize(symbol, event):

    btl_size = str(calcBootloaderSize())

    symbol.setValue(btl_size)
    symbol.setVisible(True)

def setTriggerLenVisible(symbol, event):
    symbol.setVisible(event["value"])

def hasHwCRCGenerator():
    for module in range (0, len(peripherals)):
        periphName = str(peripherals[module].getAttribute("name"))
        if (periphName == "DSU"):
            res = Database.activateComponents(["dsu"])
            return True

    return False

def setupCoreComponentSymbols():

    coreComponent = Database.getComponentByID("core")

    # Disable core related file generation not required for bootloader
    coreComponent.getSymbolByID("CoreMainFile").setValue(False)

    coreComponent.getSymbolByID("CoreSysInitFile").setValue(False)

    coreComponent.getSymbolByID("CoreSysStartupFile").setValue(False)

    coreComponent.getSymbolByID("CoreSysCallsFile").setValue(False)

    coreComponent.getSymbolByID("CoreSysIntFile").setValue(False)

    coreComponent.getSymbolByID("CoreSysExceptionFile").setValue(False)

    coreComponent.getSymbolByID("CoreSysStdioSyscallsFile").setValue(False)

    # Enable PAC component if present
    for module in range (0, len(peripherals)):
        periphName = str(peripherals[module].getAttribute("name"))
        if (periphName == "PAC"):
            coreComponent.getSymbolByID("PAC_USE").setValue(True)
            if (Database.getSymbolValue("core", "PAC_INTERRRUPT_MODE") != None):
                coreComponent.getSymbolByID("PAC_INTERRRUPT_MODE").setValue(False)

def instantiateComponent(bootloaderComponent):
    global ram_start
    global ram_size

    global flash_start
    global flash_size
    global flash_erase_size

    configName = Variables.get("__CONFIGURATION_NAME")

    setupCoreComponentSymbols()

    btlDualBank = bootloaderComponent.createBooleanSymbol("BTL_DUAL_BANK", None)
    btlDualBank.setLabel("Use Dual Bank For Safe Flash Update")
    if (("SAME5" in Variables.get("__PROCESSOR")) or ("SAMD5" in Variables.get("__PROCESSOR"))):
        btlDualBank.setVisible(True)
    else:
        btlDualBank.setVisible(False)

    btlDualBankComment = bootloaderComponent.createCommentSymbol("BTL_DUAL_BANK_COMMENT", None)
    btlDualBankComment.setLabel("!!! WARNING Only Half of the Flash memory will be available for Application !!!")
    btlDualBankComment.setVisible(False)
    btlDualBankComment.setDependencies(setBtlDualBankCommentVisible, ["BTL_DUAL_BANK"])

    btlPeriphUsed = bootloaderComponent.createStringSymbol("PERIPH_USED", None)
    btlPeriphUsed.setLabel("Bootloader Peripheral Used")
    btlPeriphUsed.setReadOnly(True)
    btlPeriphUsed.setDefaultValue("")

    btlMemUsed = bootloaderComponent.createStringSymbol("MEM_USED", None)
    btlMemUsed.setLabel("Bootloader Memory Used")
    btlMemUsed.setReadOnly(True)
    btlMemUsed.setDefaultValue("")

    btl_size = calcBootloaderSize()

    btlSize = bootloaderComponent.createStringSymbol("BTL_SIZE", None)
    btlSize.setLabel("Bootloader Size (Bytes)")
    btlSize.setVisible(False)
    btlSize.setDefaultValue(str(btl_size))
    btlSize.setDependencies(setBootloaderSize, ["MEM_USED"])

    btlSizeComment = bootloaderComponent.createCommentSymbol("BTL_SIZE_COMMENT", None)
    btlSizeComment.setLabel("!!! Bootloader size should be aligned to Erase Unit Size of the device !!!")
    btlSizeComment.setVisible(True)

    btlTriggerEnable = bootloaderComponent.createBooleanSymbol("BTL_TRIGGER_ENABLE", None)
    btlTriggerEnable.setLabel("Enable Bootloader Trigger From Firmware")
    btlTriggerEnable.setDescription("This Option can be used to Force Trigger bootloader from application firmware after a soft reset.")

    btlTriggerLenDesc = "This option adds the provided offset to RAM Start address in bootloader linker script. \
                         Application firmware can store some pattern in the reserved bytes region from RAM start for bootloader \
                         to check at reset."
    btlTriggerLen = bootloaderComponent.createStringSymbol("BTL_TRIGGER_LEN", btlTriggerEnable)
    btlTriggerLen.setLabel("Number Of Bytes To Reserve From Start Of RAM")
    btlTriggerLen.setVisible((btlTriggerEnable.getValue() == True))
    btlTriggerLen.setDefaultValue("0")
    btlTriggerLen.setDependencies(setTriggerLenVisible, ["BTL_TRIGGER_ENABLE"])
    btlTriggerLen.setDescription(btlTriggerLenDesc)

    btlRamStart = bootloaderComponent.createStringSymbol("BTL_RAM_START", None)
    btlRamStart.setDefaultValue(ram_start)
    btlRamStart.setReadOnly(True)
    btlRamStart.setVisible(False)

    btlRamSize = bootloaderComponent.createStringSymbol("BTL_RAM_SIZE", None)
    btlRamSize.setDefaultValue(ram_size)
    btlRamSize.setReadOnly(True)
    btlRamSize.setVisible(False)

    btlAppAddrComment = bootloaderComponent.createCommentSymbol("BTL_APP_START_ADDR_COMMENT", None)
    btlAppAddrComment.setVisible(False)
    btlAppAddrComment.setDependencies(setAppStartAndCommentVisible, ["core.APP_START_ADDRESS", "BTL_SIZE"])

    btlHwCrc = bootloaderComponent.createBooleanSymbol("BTL_HW_CRC_GEN", None)
    btlHwCrc.setLabel("Bootloader Hardware CRC Generator")
    btlHwCrc.setReadOnly(True)
    btlHwCrc.setVisible(False)
    btlHwCrc.setDefaultValue(hasHwCRCGenerator())

    #################### Code Generation ####################

    btlSourceFile = bootloaderComponent.createFileSymbol("BOOTLOADER_SRC", None)
    btlSourceFile.setSourcePath("../bootloader/templates/arm/bootloader_uart.c.ftl")
    btlSourceFile.setOutputName("bootloader.c")
    btlSourceFile.setMarkup(True)
    btlSourceFile.setOverwrite(True)
    btlSourceFile.setDestPath("/bootloader/")
    btlSourceFile.setProjectPath("config/" + configName + "/bootloader/")
    btlSourceFile.setType("SOURCE")

    btlHeaderFile = bootloaderComponent.createFileSymbol("BOOTLOADER_HEADER", None)
    btlHeaderFile.setSourcePath("../bootloader/templates/bootloader.h.ftl")
    btlHeaderFile.setOutputName("bootloader.h")
    btlHeaderFile.setMarkup(True)
    btlHeaderFile.setOverwrite(True)
    btlHeaderFile.setDestPath("/bootloader/")
    btlHeaderFile.setProjectPath("config/" + configName + "/bootloader/")
    btlHeaderFile.setType("HEADER")

    # generate main.c file
    btlmainSourceFile = bootloaderComponent.createFileSymbol("MAIN_BOOTLOADER_C", None)
    btlmainSourceFile.setSourcePath("../bootloader/templates/system/main.c.ftl")
    btlmainSourceFile.setOutputName("main.c")
    btlmainSourceFile.setMarkup(True)
    btlmainSourceFile.setOverwrite(False)
    btlmainSourceFile.setDestPath("../../")
    btlmainSourceFile.setProjectPath("")
    btlmainSourceFile.setType("SOURCE")

    # generate startup_xc32.c file
    btlStartSourceFile = bootloaderComponent.createFileSymbol("STARTUP_BOOTLOADER_C", None)
    btlStartSourceFile.setSourcePath("../bootloader/templates/arm/startup_xc32.c.ftl")
    btlStartSourceFile.setOutputName("startup_xc32.c")
    btlStartSourceFile.setMarkup(True)
    btlStartSourceFile.setOverwrite(True)
    btlStartSourceFile.setDestPath("")
    btlStartSourceFile.setProjectPath("config/" + configName + "/")
    btlStartSourceFile.setType("SOURCE")

    # Generate Initialization File
    btlInitFile = bootloaderComponent.createFileSymbol("INITIALIZATION_BOOTLOADER_C", None)
    btlInitFile.setSourcePath("../bootloader/templates/arm/initialization.c.ftl")
    btlInitFile.setOutputName("initialization.c")
    btlInitFile.setMarkup(True)
    btlInitFile.setOverwrite(True)
    btlInitFile.setDestPath("")
    btlInitFile.setProjectPath("config/" + configName + "/")
    btlInitFile.setType("SOURCE")

    # Generate Bootloader Linker Script
    btlLinkerFile = bootloaderComponent.createFileSymbol("BOOTLOADER_LINKER_FILE", None)
    btlLinkerFile.setSourcePath("../bootloader/templates/arm/bootloader_linker.ld.ftl")
    btlLinkerFile.setOutputName("btl.ld")
    btlLinkerFile.setMarkup(True)
    btlLinkerFile.setOverwrite(True)
    btlLinkerFile.setType("LINKER")

    btlSystemDefFile = bootloaderComponent.createFileSymbol("BTL_SYS_DEF_HEADER", None)
    btlSystemDefFile.setType("STRING")
    btlSystemDefFile.setOutputName("core.LIST_SYSTEM_DEFINITIONS_H_INCLUDES")
    btlSystemDefFile.setSourcePath("../bootloader/templates/system/definitions.h.ftl")
    btlSystemDefFile.setMarkup(True)

    # set XC32 option to not use the CRT0 startup code
    xc32NoCRT0StartupCodeSym = bootloaderComponent.createSettingSymbol("XC32_NO_CRT0_STARTUP_CODE", None)
    xc32NoCRT0StartupCodeSym.setCategory("C32-LD")
    xc32NoCRT0StartupCodeSym.setKey("no-startup-files")
    xc32NoCRT0StartupCodeSym.setValue("true")

    # Clear Placing data into its own section
    xc32ClearDataSection = bootloaderComponent.createSettingSymbol("XC32_CLEAR_DATA_SECTION", None)
    xc32ClearDataSection.setCategory("C32")
    xc32ClearDataSection.setKey("place-data-into-section")
    xc32ClearDataSection.setValue("false")

def onAttachmentConnected(source, target):
    global flash_erase_size

    localComponent = source["component"]
    remoteComponent = target["component"]
    remoteID = remoteComponent.getID()
    srcID = source["id"]
    targetID = target["id"]

    if (srcID == "btl_UART_dependency"):
        periph_name = Database.getSymbolValue(remoteID, "USART_PLIB_API_PREFIX")

        localComponent.getSymbolByID("PERIPH_USED").clearValue()
        localComponent.getSymbolByID("PERIPH_USED").setValue(periph_name)

        Database.setSymbolValue(remoteID, "USART_INTERRUPT_MODE", False)

        coreComponent = Database.getComponentByID("core")

        # Enable Systick.
        coreComponent.getSymbolByID("systickEnable").setValue(True)

        # Configure systick period to 100 ms
        coreComponent.getSymbolByID("SYSTICK_PERIOD_MS").setValue(100)

    if (srcID == "btl_MEMORY_dependency"):
        flash_erase_size = int(Database.getSymbolValue(remoteID, "FLASH_ERASE_SIZE"))
        localComponent.getSymbolByID("MEM_USED").setValue(remoteID.upper())

        Database.setSymbolValue(remoteID, "INTERRUPT_ENABLE", False)

def onAttachmentDisconnected(source, target):
    global flash_erase_size

    localComponent = source["component"]
    remoteComponent = target["component"]
    remoteID = remoteComponent.getID()
    srcID = source["id"]
    targetID = target["id"]

    if (srcID == "btl_UART_dependency"):
        localComponent.getSymbolByID("PERIPH_USED").clearValue()

        coreComponent = Database.getComponentByID("core")

        # Disable Systick
        coreComponent.getSymbolByID("systickEnable").setValue(False)

    if (srcID == "btl_MEMORY_dependency"):
        flash_erase_size = 0
        localComponent.getSymbolByID("MEM_USED").clearValue()
