
ANSIBLE_TAGS=ENV['ANSIBLE_TAGS']

Vagrant.configure("2") do |config|

    config.vm.box = "wholebits/ubuntu17.04-64"

    # Log in as root always to avoid ansible unprivileged user troubles, see:
    # https://docs.ansible.com/ansible/become.html#becoming-an-unprivileged-user
    config.ssh.username = "root"
    config.ssh.password = "vagrant"
    config.ssh.insert_key = true

    # config.vm.network "forwarded_port", guest: 8080, host: 8080
    config.vm.network "forwarded_port", guest: 80, host: 5000

    config.vm.synced_folder ".", "/vagrant", disabled: true

    config.vm.synced_folder ".", "/home/atuser/adventure-track"

    config.vm.provider "virtualbox" do |vb|
        vb.memory = "1024"
        vb.cpus = 2
    end

    config.vm.provision :ansible do |ansible|
        # Use `export ANSIBLE_TAGS="tag1,tag2"; vagrant provision`
        ansible.tags = ANSIBLE_TAGS
        ansible.playbook = "ansible/vagrant-playbook.yml"
    end
end
