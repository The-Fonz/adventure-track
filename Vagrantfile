
ANSIBLE_TAGS=ENV['ANSIBLE_TAGS']

Vagrant.configure("2") do |config|

    config.vm.box = "bento/ubuntu-16.04"

    config.vm.network "forwarded_port", guest: 80, host: 8080

    config.vm.synced_folder ".", "/vagrant", disabled: true

    config.vm.synced_folder ".", "/home/causer/come-along"

    config.vm.provider "virtualbox" do |vb|
        vb.memory = "512"
    end

    config.vm.provision :ansible do |ansible|
        # Use export ANSIBLE_TAGS="tag1,tag2"; vagrant provision
        ansible.tags = ANSIBLE_TAGS
        ansible.playbook = "playbook.yml"
    end
end