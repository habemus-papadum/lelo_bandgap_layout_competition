# All inputs arrive through environment variables, never interpolated Tcl code.
if {[catch {
    set top $env(BG_TOP)
    set exdir [file join [pwd] ext]
    set netlist [file join [pwd] raw.spice]
    load [file join $env(BG_CELLS) ${top}.mag]
    select top cell
    expand
    if {$env(BG_ACTION) eq "drc"} {
        drc style $env(BG_DRC_STYLE)
        drc check
        drc catchup
        set count 0
        foreach {rule boxes} [drc listall why] {
            puts "RULE: $rule"
            foreach coords $boxes {puts "BOX: $coords"}
            incr count [llength $boxes]
        }
        puts "BG_DRC_COUNT $count"
    } elseif {$env(BG_ACTION) eq "area"} {
        flatten -nolabels area
        load area
        puts "BG_SCALE [cif scale out]"
        save area.mag
    } elseif {$env(BG_ACTION) eq "lvs"} {
        file mkdir ext
        extract path $exdir
        extract all
        ext2spice lvs
        ext2spice -p $exdir -o $netlist
    } else {
        flatten ${top}_flat
        load ${top}_flat
        cellname delete $top
        select top cell
        file mkdir ext
        extract path $exdir
        if {$env(BG_MODE) eq "rc"} {
            extract do resistance
            extract do capacitance
            extract do coupling
        }
        extract all
        if {$env(BG_MODE) eq "rc"} {
            ext2sim labels on
            ext2sim -p $exdir
            extresist tolerance $env(BG_RTOL)
            extresist all
        }
        ext2spice lvs
        ext2spice cthresh $env(BG_CTHRESH)
        if {$env(BG_MODE) eq "rc"} {ext2spice extresist on}
        ext2spice -p $exdir -o $netlist
    }
    puts BG_DONE
} message]} {puts "BG_ERROR: $message"}
quit -noprompt
