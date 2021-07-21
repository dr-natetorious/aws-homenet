# Prerequisit:
#    aws s3 ls --recursive s3://homenet-hybrid.us-east-1.virtual.world/eufy/moonbase.cameras.real.world/ > moonbase.txt
#    aws s3 ls --recursive s3://homenet-hybrid.us-east-1.virtual.world/eufy/starbase.cameras.real.world/ > starbase.txt

function read_files {
    Write-Verbose "Loading starbase.txt..."
    $starbase = gc .\starbase.txt
    Write-Verbose "Loading moonbasebase.txt..."
    $moonbase = gc .\moonbase.txt

    Write-Verbose "Filtering..."
    $object_keys = $starbase + $moonbase
    $object_keys = $object_keys | %{ $_.substring("2021-05-28 20:59:58    1279819 ".length) }
    return $object_keys
}

function get_object_keys([System.Collections.IEnumerable] $s3_keys) {

    Write-Verbose "Pipelining..." 
    return $s3_keys | %{ 
        echo "$_"
        $object_key = $_        
        
        $split = $object_key.split('/')
        if ($split.length -lt 8){
            continue
        }


        $frame_info = [PSCustomObject] @{
            base_name = $split[1]
            camera_name = $split[2]
            year = [int]::Parse($split[3])
            month = [int]::Parse($split[4])
            day = [int]::Parse($split[5])
            hour = [int]::Parse($split[6])
            min = [int]::Parse($split[7])
            offset = $split[8]
            s3_key = $object_key
        }

        return $frame_info
    }
}

function group_at_resolution([System.Collections.IEnumerable] $s3_keys, [int] $depth) {

    $map = New-Object System.Collections.Hashtable
    foreach($object in $s3_keys){
        $prefix = [string]::Join('/', ($object.split('/') | Select-Object -First $depth))
        if($map.ContainsKey($prefix) -eq $false){
            $map[$prefix] = New-Object System.Collections.ArrayList
        }

        $map[$prefix].Add($object) | Out-Null
    }

    return $map
}

function sample_set([System.Collections.IDictionary] $map, [int] $count){
    $list = New-Object System.Collections.ArrayList
    $rand = New-Object System.Random
    $map_keys = $map.Keys | %{ $_ }


    foreach($_ in [System.Linq.Enumerable]::Range(0, $count)){
        $scene_id = $map_keys[ $rand.Next($map.Keys.Count -1) ] 
        $scene = $map[$scene_id]
        if ($scene -is [System.Collections.ArrayList]){
            $scene = $scene[$rand.Next($scene.Count-1)]
        }
        $frame = $scene[ $rand.Next($scene.Length) ]
        $list.Add($frame) | Out-Null
    }

    return $list
}

$file_entries = read_files
$object_keys = get_object_keys $file_entries 
