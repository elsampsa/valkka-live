#!/bin/bash
grep -rl "my_pyramid_example" * | xargs sed -i s@"my\_pyramid\_example"@"valkka\.web"@g
