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

import re

global ram_start
global ram_size

global flash_start
global flash_size
global flash_erase_size

global btl_start

flash_start         = 0
flash_size          = 0
flash_erase_size    = 0

btl_start           = "0x9FC01000"

BootFlashNames      = ["bootconfig"]
ProgramFlashNames   = ["code"]
RamNames            = ["kseg0_data_mem", "kseg1_data_mem"]

addr_space          = ATDF.getNode("/avr-tools-device-file/devices/device/address-spaces/address-space")
addr_space_children = addr_space.getChildren()

for mem_idx in range(0, len(addr_space_children)):
    mem_seg     = addr_space_children[mem_idx].getAttribute("name")
    mem_type    = addr_space_children[mem_idx].getAttribute("type")

    if ((any(x == mem_seg for x in ProgramFlashNames) == True)):
        flash_start = int(addr_space_children[mem_idx].getAttribute("start"), 16)
        flash_size  = int(addr_space_children[mem_idx].getAttribute("size"), 16)

    if ((any(x == mem_seg for x in RamNames) == True)):
        if (mem_seg == "kseg0_data_mem"):
            ram_start   = "0x80000000"
        else:
            ram_start   = "0xA0000000"
        ram_size    = addr_space_children[mem_idx].getAttribute("size")

    if ("PIC32MX" in Variables.get("__PROCESSOR")):
        if ((any(x == mem_seg for x in BootFlashNames) == True)):
            if (addr_space_children[mem_idx].getAttribute("size") == "0xbf0"):
                # Bootloader start address is in Program Flash memory as Boot Flash Memory is only 3KB
                btl_start = "0x9D000000"
            else:
                btl_start = "0x9FC00500"

def calcBootloaderSize():
    global flash_erase_size

    # Calculated values with Optimization level -O1
    if ("PIC32MX" in Variables.get("__PROCESSOR")):
        max_uart_btl_size   = 4096
    else:
        max_uart_btl_size   = 8192

    btl_size                = 0

    if (flash_erase_size != 0):
        if (flash_erase_size >= max_uart_btl_size):
            btl_size = flash_erase_size
        else:
            btl_size = max_uart_btl_size


    return btl_size

def setBootloaderSize(symbol, event):

    btl_size = str(calcBootloaderSize())

    symbol.setValue(btl_size)
    symbol.setVisible(True)

def setTriggerLenVisible(symbol, event):
    symbol.setVisible(event["value"])

def setBtlDualBankCommentVisible(symbol, event):
    symbol.setVisible(event["value"])

def setAppStartAndCommentVisible(symbol, event):
    global flash_start
    global flash_size

    if (btl_start == "0x9D000000"):
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

def instantiateComponent(bootloaderComponent):
    global btlStart
    global ram_start
    global ram_size

    global flash_start
    global flash_size
    global flash_erase_size

    configName = Variables.get("__CONFIGURATION_NAME")

    setupCoreComponentSymbols()

    btlDualBank = bootloaderComponent.createBooleanSymbol("BTL_DUAL_BANK", None)
    btlDualBank.setLabel("Use Dual Bank For Safe Flash Update")
    if ("PIC32MX" in Variables.get("__PROCESSOR")):
        btlDualBank.setVisible(False)

    btlDualBankComment = bootloaderComponent.createCommentSymbol("BTL_DUAL_BANK_COMMENT", None)
    btlDualBankComment.setLabel("!!! WARNING Only Half of the Program Flash memory will be available for Application !!!")
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

    btlStart = bootloaderComponent.createStringSymbol("BTL_START", None)
    btlStart.setLabel("Bootloader Start Address")
    btlStart.setVisible(False)
    btlStart.setDefaultValue(btl_start)

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

    if ("PIC32MX" in Variables.get("__PROCESSOR")):
        btlAppAddrComment = bootloaderComponent.createCommentSymbol("BTL_APP_START_ADDR_COMMENT", None)
        btlAppAddrComment.setVisible(False)
        btlAppAddrComment.setDependencies(setAppStartAndCommentVisible, ["core.APP_START_ADDRESS", "BTL_SIZE"])

    #################### Code Generation ####################

    btlSourceFile = bootloaderComponent.createFileSymbol("BOOTLOADER_SRC", None)
    btlSourceFile.setSourcePath("../bootloader/templates/mips/bootloader_uart.c.ftl")
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

    # Generate Initialization File
    btlInitFile = bootloaderComponent.createFileSymbol("INITIALIZATION_BOOTLOADER_C", None)
    btlInitFile.setSourcePath("../bootloader/templates/mips/initialization.c.ftl")
    btlInitFile.setOutputName("initialization.c")
    btlInitFile.setMarkup(True)
    btlInitFile.setOverwrite(True)
    btlInitFile.setDestPath("")
    btlInitFile.setProjectPath("config/" + configName + "/")
    btlInitFile.setType("SOURCE")

    # Generate Bootloader Linker Script
    btlLinkerPath = "../bootloader/templates/mips/linkers/"

    btlLinkerFile = bootloaderComponent.createFileSymbol("BOOTLOADER_LINKER_FILE", None)

    if (re.match("PIC32MZ.[0-9]*EF", Variables.get("__PROCESSOR"))):
        btlLinkerFile.setSourcePath(btlLinkerPath + "bootloader_linker_mz_ef.ld.ftl")
    elif (re.match("PIC32MZ.[0-9]*DA", Variables.get("__PROCESSOR"))):
        btlLinkerFile.setSourcePath(btlLinkerPath + "bootloader_linker_mz_da.ld.ftl")
    elif (re.match("PIC32MK.[0-9]*GPD", Variables.get("__PROCESSOR")) or
          re.match("PIC32MK.[0-9]*GPE", Variables.get("__PROCESSOR")) or
          re.match("PIC32MK.[0-9]*MCF", Variables.get("__PROCESSOR"))):
        btlLinkerFile.setSourcePath(btlLinkerPath + "bootloader_linker_mk_gpd_gpe_mcf.ld.ftl")
    elif (re.match("PIC32MK.[0-9]*GPG", Variables.get("__PROCESSOR")) or
          re.match("PIC32MK.[0-9]*GPH", Variables.get("__PROCESSOR")) or
          re.match("PIC32MK.[0-9]*MCJ", Variables.get("__PROCESSOR"))):
        btlDualBank.setVisible(False)
        btlLinkerFile.setSourcePath(btlLinkerPath + "bootloader_linker_mk_gpg_gph_mcj.ld.ftl")
    elif (re.match("PIC32MK.[0-9]*GPK", Variables.get("__PROCESSOR")) or
          re.match("PIC32MK.[0-9]*GPL", Variables.get("__PROCESSOR")) or
          re.match("PIC32MK.[0-9]*MCM", Variables.get("__PROCESSOR"))):
        btlLinkerFile.setSourcePath(btlLinkerPath + "bootloader_linker_mk_gpk_gpl_mcm.ld.ftl")
    elif (re.match("PIC32MX1.[1235]*0F.[0-9]*.[BCD]", Variables.get("__PROCESSOR")) or
          re.match("PIC32MX2.[1235]*0F.[0-9]*.[BCD]", Variables.get("__PROCESSOR"))):
        btlLinkerFile.setSourcePath(btlLinkerPath + "bootloader_linker_mx_1xx_2xx.ld.ftl")
    elif (re.match("PIC32MX1.[57]*4F.[0-9]*.[BD]", Variables.get("__PROCESSOR")) or
          re.match("PIC32MX2.[57]*4F.[0-9]*.[BD]", Variables.get("__PROCESSOR"))):
        btlLinkerFile.setSourcePath(btlLinkerPath + "bootloader_linker_mx_1xx_2xx_xlp.ld.ftl")
    elif (re.match("PIC32MX1.[2357]*0F.[0-9]*.[HL]", Variables.get("__PROCESSOR")) or
          re.match("PIC32MX2.[357]*0F.[0-9]*.[HL]", Variables.get("__PROCESSOR")) or
          re.match("PIC32MX5.[357]*0F.[0-9]*.[HL]", Variables.get("__PROCESSOR"))):
        btlLinkerFile.setSourcePath(btlLinkerPath + "bootloader_linker_mx_1xx_2xx_5xx.ld.ftl")
    elif (re.match("PIC32MX3.[357]*0F.[0-9]*.[HL]", Variables.get("__PROCESSOR")) or
          re.match("PIC32MX4.[357]*0F.[0-9]*.[HL]", Variables.get("__PROCESSOR"))):
        btlLinkerFile.setSourcePath(btlLinkerPath + "bootloader_linker_mx_3xx_4xx.ld.ftl")
    elif (re.match("PIC32MX5.[367]*.[45]*F.[0-9]*.[HL]", Variables.get("__PROCESSOR")) or
          re.match("PIC32MX6.[679]*.[45]*F.[0-9]*.[HL]", Variables.get("__PROCESSOR")) or
          re.match("PIC32MX7.[679]*.[45]*F.[0-9]*.[HL]", Variables.get("__PROCESSOR"))):
        btlLinkerFile.setSourcePath(btlLinkerPath + "bootloader_linker_mx_5xx_6xx_7xx.ld.ftl")

    btlLinkerFile.setOutputName("btl.ld")
    btlLinkerFile.setMarkup(True)
    btlLinkerFile.setOverwrite(True)
    btlLinkerFile.setType("LINKER")

    btlSystemDefFile = bootloaderComponent.createFileSymbol("BTL_SYS_DEF_HEADER", None)
    btlSystemDefFile.setType("STRING")
    btlSystemDefFile.setOutputName("core.LIST_SYSTEM_DEFINITIONS_H_INCLUDES")
    btlSystemDefFile.setSourcePath("../bootloader/templates/system/definitions.h.ftl")
    btlSystemDefFile.setMarkup(True)

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

    if (srcID == "btl_MEMORY_dependency"):
        flash_erase_size = 0
        localComponent.getSymbolByID("MEM_USED").clearValue()
