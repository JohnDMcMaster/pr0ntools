INSTALL_DIR=~/.config/inkscape/extensions
	
NAME=pr0nliner

install:
	mkdir -p $(INSTALL_DIR)
	cp $(NAME).inx $(NAME).py $(INSTALL_DIR)
	chmod a+x $(INSTALL_DIR)/$(NAME).py $(INSTALL_DIR)/$(NAME).inx

install_link:
	mkdir -p $(INSTALL_DIR)
	chmod a+x $(NAME).py $(NAME).inx
	ln -s $(PWD)/$(NAME).py $(INSTALL_DIR)
	ln -s $(PWD)/$(NAME).inx $(INSTALL_DIR)
	
